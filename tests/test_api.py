from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_complete_auditable_vertical_slice():
    place = client.post(
        "/places",
        json={
            "name": "Example Cultural Place",
            "place_type": "heritage attraction",
            "diagnostic_scope": "Test whether holiday traffic evidence weakens a low-awareness hypothesis.",
        },
    )
    assert place.status_code == 201
    place_id = place.json()["id"]

    evidence = client.post(
        "/evidence",
        json={
            "place_id": place_id,
            "title": "Official visitor statistics",
            "source_type": "official",
            "excerpt": "The site received 80,000 visitors during the holiday period.",
            "reliability": "HIGH",
        },
    )
    assert evidence.status_code == 201
    evidence_id = evidence.json()["id"]

    finding = client.post(
        "/findings",
        json={
            "place_id": place_id,
            "statement": "The site received about eighty thousand visitors.",
            "dimension": "VISIBILITY",
            "evidence_ids": [evidence_id],
            "generated_by": "test-model",
        },
    )
    assert finding.status_code == 201
    finding_id = finding.json()["id"]

    reviewed = client.patch(
        f"/findings/{finding_id}/verify",
        json={
            "status": "EDITED",
            "human_revision": "The source reports 80,000 visitors during the reported holiday period.",
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["verification_status"] == "EDITED"
    assert reviewed.json()["original_statement"] == "The site received about eighty thousand visitors."
    assert reviewed.json()["statement"] == "The source reports 80,000 visitors during the reported holiday period."

    gap = client.post(
        "/gaps",
        json={
            "place_id": place_id,
            "from_dimension": "VISIBILITY",
            "to_dimension": "CONVERSION",
            "description": "Observed holiday traffic does not establish whether visibility converts into durable place value.",
            "finding_ids": [finding_id],
        },
    )
    assert gap.status_code == 201
    gap_id = gap.json()["id"]

    hypothesis = client.post(
        "/hypotheses",
        json={
            "place_id": place_id,
            "gap_id": gap_id,
            "statement": "Low visitor awareness may not be the primary bottleneck during major holiday periods.",
            "supporting_evidence_ids": [evidence_id],
            "alternative_explanations": [
                "Holiday traffic may not represent normal-period awareness.",
                "Visitors may be arriving for adjacent attractions rather than this place itself."
            ],
            "confidence": "MEDIUM",
            "confidence_reason": "One high-reliability source supports holiday traffic, but temporal representativeness is limited."
        },
    )
    assert hypothesis.status_code == 201
    hypothesis_id = hypothesis.json()["id"]

    evidence_need = client.post(
        "/evidence-needs",
        json={
            "place_id": place_id,
            "related_hypothesis_id": hypothesis_id,
            "question": "What proportion of visitors identify this place as their primary trip purpose?",
            "why_it_matters": "This would distinguish destination awareness from incidental holiday traffic.",
            "recommended_method": "Visitor intercept survey",
            "priority": "HIGH"
        },
    )
    assert evidence_need.status_code == 201

    state = client.get(f"/places/{place_id}/diagnostic-state")
    assert state.status_code == 200
    body = state.json()
    assert len(body["evidence"]) == 1
    assert len(body["findings"]) == 1
    assert len(body["gaps"]) == 1
    assert len(body["hypotheses"]) == 1
    assert len(body["evidence_needs"]) == 1


def test_cross_place_evidence_is_rejected():
    first = client.post(
        "/places",
        json={"name": "Place A", "diagnostic_scope": "A"},
    ).json()
    second = client.post(
        "/places",
        json={"name": "Place B", "diagnostic_scope": "B"},
    ).json()

    evidence = client.post(
        "/evidence",
        json={
            "place_id": first["id"],
            "title": "Evidence for A",
            "source_type": "official",
            "excerpt": "Evidence belongs to Place A."
        },
    ).json()

    response = client.post(
        "/findings",
        json={
            "place_id": second["id"],
            "statement": "This must not be allowed.",
            "dimension": "RESOURCE",
            "evidence_ids": [evidence["id"]]
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Evidence must belong to the same Place"


def test_edit_requires_human_revision():
    place = client.post(
        "/places",
        json={"name": "Review Test", "diagnostic_scope": "Review semantics"},
    ).json()
    evidence = client.post(
        "/evidence",
        json={
            "place_id": place["id"],
            "title": "Source",
            "source_type": "other",
            "excerpt": "A directly observable statement."
        },
    ).json()
    finding = client.post(
        "/findings",
        json={
            "place_id": place["id"],
            "statement": "A directly observable statement.",
            "dimension": "RESOURCE",
            "evidence_ids": [evidence["id"]]
        },
    ).json()

    response = client.patch(
        f"/findings/{finding['id']}/verify",
        json={"status": "EDITED"},
    )
    assert response.status_code == 422
