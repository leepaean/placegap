from fastapi import FastAPI
from pydantic import BaseModel
from uuid import UUID

from core.models import Evidence, Finding, Hypothesis, Place, VerificationStatus

app = FastAPI(
    title="PlaceGap API",
    version="0.0.1",
    description="Evidence-backed diagnostics for cultural places.",
)

places: dict[UUID, Place] = {}
evidence_store: dict[UUID, Evidence] = {}
findings: dict[UUID, Finding] = {}
hypotheses: dict[UUID, Hypothesis] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.0.1"}


@app.post("/places", response_model=Place)
def create_place(place: Place) -> Place:
    places[place.id] = place
    return place


@app.post("/evidence", response_model=Evidence)
def create_evidence(evidence: Evidence) -> Evidence:
    if evidence.place_id not in places:
        raise ValueError("Unknown place_id")
    evidence_store[evidence.id] = evidence
    return evidence


@app.post("/findings", response_model=Finding)
def create_finding(finding: Finding) -> Finding:
    if finding.place_id not in places:
        raise ValueError("Unknown place_id")
    missing = [eid for eid in finding.evidence_ids if eid not in evidence_store]
    if missing:
        raise ValueError(f"Unknown evidence_ids: {missing}")
    findings[finding.id] = finding
    return finding


class FindingVerification(BaseModel):
    status: VerificationStatus
    human_revision: str | None = None


@app.patch("/findings/{finding_id}/verify", response_model=Finding)
def verify_finding(finding_id: UUID, payload: FindingVerification) -> Finding:
    finding = findings[finding_id]
    updated = finding.model_copy(update={
        "verification_status": payload.status,
        "human_revision": payload.human_revision,
    })
    findings[finding_id] = updated
    return updated


@app.post("/hypotheses", response_model=Hypothesis)
def create_hypothesis(hypothesis: Hypothesis) -> Hypothesis:
    if hypothesis.place_id not in places:
        raise ValueError("Unknown place_id")
    all_ids = hypothesis.supporting_evidence_ids + hypothesis.contradicting_evidence_ids
    missing = [eid for eid in all_ids if eid not in evidence_store]
    if missing:
        raise ValueError(f"Unknown evidence_ids: {missing}")
    hypotheses[hypothesis.id] = hypothesis
    return hypothesis


@app.get("/places/{place_id}/diagnostic-state")
def diagnostic_state(place_id: UUID) -> dict:
    if place_id not in places:
        raise ValueError("Unknown place_id")
    return {
        "place": places[place_id],
        "evidence": [x for x in evidence_store.values() if x.place_id == place_id],
        "findings": [x for x in findings.values() if x.place_id == place_id],
        "hypotheses": [x for x in hypotheses.values() if x.place_id == place_id],
    }
