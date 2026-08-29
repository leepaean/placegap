from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.models import (
    Evidence,
    EvidenceNeed,
    Finding,
    Gap,
    Hypothesis,
    Place,
    VerificationStatus,
)

app = FastAPI(
    title="PlaceGap API",
    version="0.0.1",
    description="Evidence-backed diagnostics for cultural places.",
)

# v0.0.1 intentionally uses in-memory stores while the domain contract is validated.
places: dict[UUID, Place] = {}
evidence_store: dict[UUID, Evidence] = {}
findings: dict[UUID, Finding] = {}
gaps: dict[UUID, Gap] = {}
hypotheses: dict[UUID, Hypothesis] = {}
evidence_needs: dict[UUID, EvidenceNeed] = {}


def require_place(place_id: UUID) -> Place:
    place = places.get(place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Unknown place_id")
    return place


def require_same_place_evidence(place_id: UUID, evidence_ids: list[UUID]) -> None:
    missing = [eid for eid in evidence_ids if eid not in evidence_store]
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"message": "Unknown evidence_ids", "ids": [str(x) for x in missing]},
        )

    wrong_place = [eid for eid in evidence_ids if evidence_store[eid].place_id != place_id]
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
def create_place(place: Place) -> Place:
    places[place.id] = place
    return place


@app.get("/places/{place_id}", response_model=Place)
def get_place(place_id: UUID) -> Place:
    return require_place(place_id)


@app.post("/evidence", response_model=Evidence, status_code=201)
def create_evidence(evidence: Evidence) -> Evidence:
    require_place(evidence.place_id)
    evidence_store[evidence.id] = evidence
    return evidence


@app.post("/findings", response_model=Finding, status_code=201)
def create_finding(finding: Finding) -> Finding:
    require_place(finding.place_id)
    require_same_place_evidence(finding.place_id, finding.evidence_ids)
    findings[finding.id] = finding
    return finding


class FindingVerification(BaseModel):
    status: VerificationStatus
    human_revision: str | None = None


@app.patch("/findings/{finding_id}/verify", response_model=Finding)
def verify_finding(finding_id: UUID, payload: FindingVerification) -> Finding:
    finding = findings.get(finding_id)
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
    findings[finding_id] = updated
    return updated


@app.post("/gaps", response_model=Gap, status_code=201)
def create_gap(gap: Gap) -> Gap:
    require_place(gap.place_id)

    missing_findings = [fid for fid in gap.finding_ids if fid not in findings]
    if missing_findings:
        raise HTTPException(
            status_code=422,
            detail={"message": "Unknown finding_ids", "ids": [str(x) for x in missing_findings]},
        )

    wrong_place = [fid for fid in gap.finding_ids if findings[fid].place_id != gap.place_id]
    if wrong_place:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Findings must belong to the same Place",
                "ids": [str(x) for x in wrong_place],
            },
        )

    gaps[gap.id] = gap
    return gap


@app.post("/hypotheses", response_model=Hypothesis, status_code=201)
def create_hypothesis(hypothesis: Hypothesis) -> Hypothesis:
    require_place(hypothesis.place_id)

    if hypothesis.gap_id is not None:
        gap = gaps.get(hypothesis.gap_id)
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
    require_same_place_evidence(hypothesis.place_id, all_ids)
    hypotheses[hypothesis.id] = hypothesis
    return hypothesis


@app.post("/evidence-needs", response_model=EvidenceNeed, status_code=201)
def create_evidence_need(evidence_need: EvidenceNeed) -> EvidenceNeed:
    require_place(evidence_need.place_id)
    hypothesis = hypotheses.get(evidence_need.related_hypothesis_id)
    if hypothesis is None:
        raise HTTPException(status_code=422, detail="Unknown related_hypothesis_id")
    if hypothesis.place_id != evidence_need.place_id:
        raise HTTPException(
            status_code=422,
            detail="Evidence Need and Hypothesis must belong to the same Place",
        )
    evidence_needs[evidence_need.id] = evidence_need
    return evidence_need


@app.get("/places/{place_id}/diagnostic-state")
def diagnostic_state(place_id: UUID) -> dict:
    place = require_place(place_id)
    return {
        "place": place,
        "evidence": [x for x in evidence_store.values() if x.place_id == place_id],
        "findings": [x for x in findings.values() if x.place_id == place_id],
        "gaps": [x for x in gaps.values() if x.place_id == place_id],
        "hypotheses": [x for x in hypotheses.values() if x.place_id == place_id],
        "evidence_needs": [
            x for x in evidence_needs.values() if x.place_id == place_id
        ],
    }
