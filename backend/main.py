from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from backend.store import SQLiteStore
from core.models import (
    Evidence,
    EvidenceNeed,
    Finding,
    Gap,
    Hypothesis,
    Place,
    VerificationStatus,
)


class FindingVerification(BaseModel):
    status: VerificationStatus
    human_revision: str | None = None


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
        version="0.0.1",
        description="Evidence-backed diagnostics for cultural places.",
        lifespan=lifespan,
    )

    def get_store(request: Request) -> SQLiteStore:
        return request.app.state.store

    def require_place(store: SQLiteStore, place_id: UUID) -> Place:
        place = store.get_place(str(place_id))
        if place is None:
            raise HTTPException(status_code=404, detail="Unknown place_id")
        return place

    def require_same_place_evidence(
        store: SQLiteStore, place_id: UUID, evidence_ids: list[UUID]
    ) -> None:
        evidence = [store.get_evidence(str(eid)) for eid in evidence_ids]
        missing = [
            eid for eid, item in zip(evidence_ids, evidence, strict=True) if item is None
        ]
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

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": "0.0.1"}

    @app.post("/places", response_model=Place, status_code=201)
    def create_place(place: Place, request: Request) -> Place:
        get_store(request).put_place(place)
        return place

    @app.get("/places/{place_id}", response_model=Place)
    def get_place(place_id: UUID, request: Request) -> Place:
        return require_place(get_store(request), place_id)

    @app.post("/evidence", response_model=Evidence, status_code=201)
    def create_evidence(evidence: Evidence, request: Request) -> Evidence:
        store = get_store(request)
        require_place(store, evidence.place_id)
        store.put_evidence(evidence)
        return evidence

    @app.post("/findings", response_model=Finding, status_code=201)
    def create_finding(finding: Finding, request: Request) -> Finding:
        store = get_store(request)
        require_place(store, finding.place_id)
        require_same_place_evidence(store, finding.place_id, finding.evidence_ids)
        store.put_finding(finding)
        return finding

    @app.patch("/findings/{finding_id}/verify", response_model=Finding)
    def verify_finding(
        finding_id: UUID, payload: FindingVerification, request: Request
    ) -> Finding:
        store = get_store(request)
        finding = store.get_finding(str(finding_id))
        if finding is None:
            raise HTTPException(status_code=404, detail="Unknown finding_id")

        original_statement = finding.original_statement
        statement = finding.statement

        if payload.status == VerificationStatus.EDITED:
            if not payload.human_revision:
                raise HTTPException(
                    status_code=422,
                    detail="human_revision is required when status is EDITED",
                )
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
        missing = [
            fid
            for fid, item in zip(gap.finding_ids, linked_findings, strict=True)
            if item is None
        ]
        if missing:
            raise HTTPException(
                status_code=422,
                detail={"message": "Unknown finding_ids", "ids": [str(x) for x in missing]},
            )
        wrong_place = [
            fid
            for fid, item in zip(gap.finding_ids, linked_findings, strict=True)
            if item is not None and item.place_id != gap.place_id
        ]
        if wrong_place:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Findings must belong to the same Place",
                    "ids": [str(x) for x in wrong_place],
                },
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

        all_ids = list(
            dict.fromkeys(
                hypothesis.supporting_evidence_ids
                + hypothesis.contradicting_evidence_ids
            )
        )
        require_same_place_evidence(store, hypothesis.place_id, all_ids)
        store.put_hypothesis(hypothesis)
        return hypothesis

    @app.post("/evidence-needs", response_model=EvidenceNeed, status_code=201)
    def create_evidence_need(
        evidence_need: EvidenceNeed, request: Request
    ) -> EvidenceNeed:
        store = get_store(request)
        require_place(store, evidence_need.place_id)
        hypothesis = store.get_hypothesis(str(evidence_need.related_hypothesis_id))
        if hypothesis is None:
            raise HTTPException(status_code=422, detail="Unknown related_hypothesis_id")
        if hypothesis.place_id != evidence_need.place_id:
            raise HTTPException(
                status_code=422,
                detail="Evidence Need and Hypothesis must belong to the same Place",
            )
        store.put_evidence_need(evidence_need)
        return evidence_need

    @app.get("/places/{place_id}/diagnostic-state")
    def diagnostic_state(place_id: UUID, request: Request) -> dict:
        store = get_store(request)
        place = require_place(store, place_id)
        key = str(place_id)
        return {
            "place": place,
            "evidence": store.list_evidence(key),
            "findings": store.list_findings(key),
            "gaps": store.list_gaps(key),
            "hypotheses": store.list_hypotheses(key),
            "evidence_needs": store.list_evidence_needs(key),
        }

    return app


app = create_app()
