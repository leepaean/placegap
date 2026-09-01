from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.llm import LLMProviderError, get_llm_config, llm_status, propose_findings_with_llm
from backend.store import SQLiteStore
from core.models import (
    Dimension,
    Evidence,
    EvidenceKind,
    EvidenceNeed,
    Finding,
    Gap,
    Hypothesis,
    Place,
    Reliability,
    Source,
    VerificationStatus,
)


class FindingVerification(BaseModel):
    status: VerificationStatus
    human_revision: str | None = None


class SourcePackSource(BaseModel):
    key: str
    title: str
    source_type: str
    source_name: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    file_reference: Optional[str] = None
    content_text: Optional[str] = None
    notes: Optional[str] = None
    reliability: Reliability = Reliability.UNRATED
    tags: list[str] = Field(default_factory=list)


class SourcePackEvidence(BaseModel):
    source_key: Optional[str] = None
    title: str
    excerpt: str
    kind: EvidenceKind = EvidenceKind.SUMMARY
    reliability: Reliability = Reliability.UNRATED
    scope: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class SourcePackPayload(BaseModel):
    sources: list[SourcePackSource] = Field(default_factory=list)
    evidence: list[SourcePackEvidence] = Field(default_factory=list)


class SourcePackImportResult(BaseModel):
    sources_created: int
    evidence_created: int


class FindingProposalRequest(BaseModel):
    evidence_ids: list[UUID]


class FindingProposal(BaseModel):
    statement: str
    dimension: Dimension
    evidence_ids: list[UUID]
    generated_by: str
    support_note: str | None = None


def split_atomic_statements(text: str) -> list[str]:
    """Conservative baseline: split Evidence text without adding any new words."""

    compact = " ".join(text.split())
    if not compact:
        return []
    parts = re.split(r"(?<=[。！？!?])\s*|(?<=\.)\s+(?=[A-Z0-9])", compact)
    return [part.strip() for part in parts if part.strip()]


def evidence_dimension(evidence: Evidence) -> Dimension:
    if evidence.scope:
        try:
            return Dimension(evidence.scope)
        except ValueError:
            pass
    return Dimension.RESOURCE


def create_app(database_path: str | Path | None = None) -> FastAPI:
    path = database_path or os.getenv("PLACEGAP_DB_PATH", "placegap.db")
    store = SQLiteStore(path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store.init()
        app.state.store = store
        yield

    app = FastAPI(
        title="PlaceGap API",
        version="0.0.3-dev",
        description="Evidence-backed diagnostics for cultural places.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_store(request: Request) -> SQLiteStore:
        return request.app.state.store

    def require_place(store: SQLiteStore, place_id: UUID) -> Place:
        place = store.get_place(str(place_id))
        if place is None:
            raise HTTPException(status_code=404, detail="Unknown place_id")
        return place

    def require_same_place_source(store: SQLiteStore, place_id: UUID, source_id: UUID) -> Source:
        source = store.get_source(str(source_id))
        if source is None:
            raise HTTPException(status_code=422, detail="Unknown source_id")
        if source.place_id != place_id:
            raise HTTPException(status_code=422, detail="Source must belong to the same Place")
        return source

    def require_same_place_evidence(
        store: SQLiteStore, place_id: UUID, evidence_ids: list[UUID]
    ) -> list[Evidence]:
        evidence = [store.get_evidence(str(eid)) for eid in evidence_ids]
        missing = [eid for eid, item in zip(evidence_ids, evidence, strict=True) if item is None]
        if missing:
            raise HTTPException(
                status_code=422,
                detail={"message": "Unknown evidence_ids", "ids": [str(x) for x in missing]},
            )
        wrong_place = [
            eid
            for eid, item in zip(evidence_ids, evidence, strict=True)
            if item is not None and item.place_id != place_id
        ]
        if wrong_place:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Evidence must belong to the same Place",
                    "ids": [str(x) for x in wrong_place],
                },
            )
        return [item for item in evidence if item is not None]

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": "0.0.3-dev"}

    @app.get("/llm/status")
    def get_llm_status() -> dict:
        return llm_status()

    @app.get("/places", response_model=list[Place])
    def list_places(request: Request) -> list[Place]:
        return get_store(request).list_places()

    @app.post("/places", response_model=Place, status_code=201)
    def create_place(place: Place, request: Request) -> Place:
        get_store(request).put_place(place)
        return place

    @app.get("/places/{place_id}", response_model=Place)
    def get_place(place_id: UUID, request: Request) -> Place:
        return require_place(get_store(request), place_id)

    @app.post("/sources", response_model=Source, status_code=201)
    def create_source(source: Source, request: Request) -> Source:
        store = get_store(request)
        require_place(store, source.place_id)
        store.put_source(source)
        return source

    @app.post(
        "/places/{place_id}/source-packs/import",
        response_model=SourcePackImportResult,
        status_code=201,
    )
    def import_source_pack(place_id: UUID, payload: SourcePackPayload, request: Request) -> SourcePackImportResult:
        store = get_store(request)
        require_place(store, place_id)

        declared_keys: set[str] = set()
        duplicate_keys: set[str] = set()
        for item in payload.sources:
            if item.key in declared_keys:
                duplicate_keys.add(item.key)
            declared_keys.add(item.key)
        if duplicate_keys:
            raise HTTPException(
                status_code=422,
                detail={"message": "Duplicate source keys", "keys": sorted(duplicate_keys)},
            )

        unknown_keys = sorted(
            {
                item.source_key
                for item in payload.evidence
                if item.source_key and item.source_key not in declared_keys
            }
        )
        if unknown_keys:
            raise HTTPException(
                status_code=422,
                detail={"message": "Evidence references unknown source keys", "keys": unknown_keys},
            )

        source_map: dict[str, Source] = {}
        for item in payload.sources:
            source = Source(
                place_id=place_id,
                title=item.title,
                source_type=item.source_type,
                source_name=item.source_name,
                author=item.author,
                published_at=item.published_at,
                url=item.url,
                file_reference=item.file_reference,
                content_text=item.content_text,
                notes=item.notes,
                reliability=item.reliability,
                tags=item.tags,
            )
            store.put_source(source)
            source_map[item.key] = source

        for item in payload.evidence:
            source = source_map.get(item.source_key) if item.source_key else None
            evidence = Evidence(
                place_id=place_id,
                source_id=source.id if source else None,
                title=item.title,
                excerpt=item.excerpt,
                kind=item.kind,
                reliability=item.reliability if item.reliability != Reliability.UNRATED else (source.reliability if source else Reliability.UNRATED),
                scope=item.scope,
                tags=item.tags,
                source_type=source.source_type if source else "other",
                source_name=source.source_name if source else None,
                author=source.author if source else None,
                published_at=source.published_at if source else None,
                url=source.url if source else None,
                file_reference=source.file_reference if source else None,
            )
            store.put_evidence(evidence)

        return SourcePackImportResult(
            sources_created=len(payload.sources),
            evidence_created=len(payload.evidence),
        )

    @app.post("/evidence", response_model=Evidence, status_code=201)
    def create_evidence(evidence: Evidence, request: Request) -> Evidence:
        store = get_store(request)
        require_place(store, evidence.place_id)
        if evidence.source_id is not None:
            source = require_same_place_source(store, evidence.place_id, evidence.source_id)
            evidence = evidence.model_copy(
                update={
                    "source_type": source.source_type,
                    "source_name": source.source_name,
                    "author": source.author,
                    "published_at": source.published_at,
                    "url": source.url,
                    "file_reference": source.file_reference,
                    "reliability": source.reliability if evidence.reliability == Reliability.UNRATED else evidence.reliability,
                }
            )
        store.put_evidence(evidence)
        return evidence

    @app.post("/places/{place_id}/finding-proposals", response_model=list[FindingProposal])
    def propose_findings(
        place_id: UUID, payload: FindingProposalRequest, request: Request
    ) -> list[FindingProposal]:
        store = get_store(request)
        place = require_place(store, place_id)
        evidence_items = require_same_place_evidence(store, place_id, payload.evidence_ids)

        config = get_llm_config()
        if config is not None:
            try:
                llm_proposals = propose_findings_with_llm(place, evidence_items)
            except LLMProviderError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            return [
                FindingProposal(
                    statement=item.statement,
                    dimension=item.dimension,
                    evidence_ids=[UUID(value) for value in item.evidence_ids],
                    generated_by=f"llm:{config.model}",
                    support_note=item.support_note,
                )
                for item in llm_proposals
            ]

        proposals: list[FindingProposal] = []
        for evidence in evidence_items:
            for statement in split_atomic_statements(evidence.excerpt):
                proposals.append(
                    FindingProposal(
                        statement=statement,
                        dimension=evidence_dimension(evidence),
                        evidence_ids=[evidence.id],
                        generated_by="evidence-text-baseline",
                        support_note="Verbatim sentence from the linked Evidence representation.",
                    )
                )
        return proposals

    @app.post("/findings", response_model=Finding, status_code=201)
    def create_finding(finding: Finding, request: Request) -> Finding:
        store = get_store(request)
        require_place(store, finding.place_id)
        require_same_place_evidence(store, finding.place_id, finding.evidence_ids)
        store.put_finding(finding)
        return finding

    @app.patch("/findings/{finding_id}/verify", response_model=Finding)
    def verify_finding(finding_id: UUID, payload: FindingVerification, request: Request) -> Finding:
        store = get_store(request)
        finding = store.get_finding(str(finding_id))
        if finding is None:
            raise HTTPException(status_code=404, detail="Unknown finding_id")

        original_statement = finding.original_statement
        statement = finding.statement
        if payload.status == VerificationStatus.EDITED:
            if not payload.human_revision:
                raise HTTPException(status_code=422, detail="human_revision is required when status is EDITED")
            original_statement = original_statement or finding.statement
            statement = payload.human_revision

        updated = finding.model_copy(
            update={
                "statement": statement,
                "verification_status": payload.status,
                "original_statement": original_statement,
                "human_revision": payload.human_revision,
            }
        )
        store.put_finding(updated)
        return updated

    @app.post("/gaps", response_model=Gap, status_code=201)
    def create_gap(gap: Gap, request: Request) -> Gap:
        store = get_store(request)
        require_place(store, gap.place_id)
        linked_findings = [store.get_finding(str(fid)) for fid in gap.finding_ids]
        missing = [fid for fid, item in zip(gap.finding_ids, linked_findings, strict=True) if item is None]
        if missing:
            raise HTTPException(status_code=422, detail={"message": "Unknown finding_ids", "ids": [str(x) for x in missing]})
        wrong_place = [
            fid
            for fid, item in zip(gap.finding_ids, linked_findings, strict=True)
            if item is not None and item.place_id != gap.place_id
        ]
        if wrong_place:
            raise HTTPException(
                status_code=422,
                detail={"message": "Findings must belong to the same Place", "ids": [str(x) for x in wrong_place]},
            )
        store.put_gap(gap)
        return gap

    @app.post("/hypotheses", response_model=Hypothesis, status_code=201)
    def create_hypothesis(hypothesis: Hypothesis, request: Request) -> Hypothesis:
        store = get_store(request)
        require_place(store, hypothesis.place_id)
        if hypothesis.gap_id is not None:
            gap = store.get_gap(str(hypothesis.gap_id))
            if gap is None:
                raise HTTPException(status_code=422, detail="Unknown gap_id")
            if gap.place_id != hypothesis.place_id:
                raise HTTPException(status_code=422, detail="Gap must belong to the same Place")
        all_ids = list(dict.fromkeys(hypothesis.supporting_evidence_ids + hypothesis.contradicting_evidence_ids))
        require_same_place_evidence(store, hypothesis.place_id, all_ids)
        store.put_hypothesis(hypothesis)
        return hypothesis

    @app.post("/evidence-needs", response_model=EvidenceNeed, status_code=201)
    def create_evidence_need(evidence_need: EvidenceNeed, request: Request) -> EvidenceNeed:
        store = get_store(request)
        require_place(store, evidence_need.place_id)
        hypothesis = store.get_hypothesis(str(evidence_need.related_hypothesis_id))
        if hypothesis is None:
            raise HTTPException(status_code=422, detail="Unknown related_hypothesis_id")
        if hypothesis.place_id != evidence_need.place_id:
            raise HTTPException(status_code=422, detail="Evidence Need and Hypothesis must belong to the same Place")
        store.put_evidence_need(evidence_need)
        return evidence_need

    @app.get("/places/{place_id}/diagnostic-state")
    def diagnostic_state(place_id: UUID, request: Request) -> dict:
        store = get_store(request)
        place = require_place(store, place_id)
        key = str(place_id)
        return {
            "place": place,
            "sources": store.list_sources(key),
            "evidence": store.list_evidence(key),
            "findings": store.list_findings(key),
            "gaps": store.list_gaps(key),
            "hypotheses": store.list_hypotheses(key),
            "evidence_needs": store.list_evidence_needs(key),
        }

    return app


app = create_app()
