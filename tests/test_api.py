from fastapi.testclient import TestClient

from backend.main import create_app


def client_for(tmp_path):
    return TestClient(create_app(tmp_path / "placegap-test.db"))


def test_complete_auditable_vertical_slice(tmp_path):
    with client_for(tmp_path) as client:
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
                "kind": "DATUM",
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
                    "Visitors may be arriving for adjacent attractions rather than this place itself.",
                ],
                "confidence": "MEDIUM",
                "confidence_reason": "One high-reliability source supports holiday traffic, but temporal representativeness is limited.",
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
                "priority": "HIGH",
            },
        )
        assert evidence_need.status_code == 201

        state = client.get(f"/places/{place_id}/diagnostic-state")
        assert state.status_code == 200
        body = state.json()
        assert body["sources"] == []
        assert len(body["evidence"]) == 1
        assert body["evidence"][0]["kind"] == "DATUM"
        assert len(body["findings"]) == 1
        assert len(body["gaps"]) == 1
        assert len(body["hypotheses"]) == 1
        assert len(body["evidence_needs"]) == 1


def test_source_and_linked_evidence_persist_across_restart(tmp_path):
    db_path = tmp_path / "persistent.db"

    with TestClient(create_app(db_path)) as client:
        place = client.post(
            "/places",
            json={"name": "Persistent Place", "diagnostic_scope": "Persistence test"},
        ).json()
        place_id = place["id"]
        source = client.post(
            "/sources",
            json={
                "place_id": place_id,
                "title": "Official bulletin",
                "source_type": "official",
                "source_name": "County government",
                "url": "https://example.test/bulletin",
                "reliability": "HIGH",
            },
        )
        assert source.status_code == 201
        source_id = source.json()["id"]

        evidence = client.post(
            "/evidence",
            json={
                "place_id": place_id,
                "source_id": source_id,
                "title": "Durable evidence",
                "excerpt": "This row should survive an application restart.",
                "kind": "QUOTE",
            },
        )
        assert evidence.status_code == 201
        assert evidence.json()["source_type"] == "official"
        assert evidence.json()["source_name"] == "County government"
        assert evidence.json()["reliability"] == "HIGH"
        assert evidence.json()["kind"] == "QUOTE"

    with TestClient(create_app(db_path)) as client:
        state = client.get(f"/places/{place_id}/diagnostic-state")
        assert state.status_code == 200
        body = state.json()
        assert body["place"]["name"] == "Persistent Place"
        assert body["sources"][0]["title"] == "Official bulletin"
        assert body["evidence"][0]["title"] == "Durable evidence"
        assert body["evidence"][0]["source_id"] == source_id
        assert body["evidence"][0]["kind"] == "QUOTE"


def test_source_pack_import_preserves_source_to_evidence_link(tmp_path):
    with client_for(tmp_path) as client:
        place = client.post(
            "/places",
            json={"name": "Pack Place", "diagnostic_scope": "Import test"},
        ).json()

        response = client.post(
            f"/places/{place['id']}/source-packs/import",
            json={
                "sources": [
                    {
                        "key": "gov-01",
                        "title": "Government visitor bulletin",
                        "source_type": "official",
                        "source_name": "Local government",
                        "reliability": "HIGH",
                        "url": "https://example.test/gov-01",
                    }
                ],
                "evidence": [
                    {
                        "source_key": "gov-01",
                        "title": "Holiday visitors",
                        "excerpt": "2026年春节期间，该景区接待游客10万人次。",
                        "kind": "DATUM",
                    }
                ],
            },
        )
        assert response.status_code == 201
        assert response.json() == {"sources_created": 1, "evidence_created": 1}

        state = client.get(f"/places/{place['id']}/diagnostic-state").json()
        assert len(state["sources"]) == 1
        assert len(state["evidence"]) == 1
        assert state["evidence"][0]["source_id"] == state["sources"][0]["id"]
        assert state["evidence"][0]["reliability"] == "HIGH"
        assert state["evidence"][0]["kind"] == "DATUM"


def test_source_pack_validation_happens_before_persistence(tmp_path):
    with client_for(tmp_path) as client:
        place = client.post(
            "/places",
            json={"name": "Invalid Pack Place", "diagnostic_scope": "Atomic import test"},
        ).json()

        response = client.post(
            f"/places/{place['id']}/source-packs/import",
            json={
                "sources": [
                    {"key": "known", "title": "Known source", "source_type": "official"}
                ],
                "evidence": [
                    {
                        "source_key": "missing",
                        "title": "Broken evidence",
                        "excerpt": "This must fail before anything is written.",
                    }
                ],
            },
        )
        assert response.status_code == 422
        state = client.get(f"/places/{place['id']}/diagnostic-state").json()
        assert state["sources"] == []
        assert state["evidence"] == []


def test_conservative_proposals_only_reuse_evidence_words(tmp_path):
    with client_for(tmp_path) as client:
        place = client.post(
            "/places",
            json={"name": "Proposal Place", "diagnostic_scope": "Proposal baseline"},
        ).json()
        evidence = client.post(
            "/evidence",
            json={
                "place_id": place["id"],
                "title": "Two statements",
                "excerpt": "2026年春节期间，该景区接待游客10万人次。该数据仅覆盖春节期间。",
                "kind": "SUMMARY",
            },
        ).json()

        response = client.post(
            f"/places/{place['id']}/finding-proposals",
            json={"evidence_ids": [evidence["id"]]},
        )
        assert response.status_code == 200
        statements = [item["statement"] for item in response.json()]
        assert statements == [
            "2026年春节期间，该景区接待游客10万人次。",
            "该数据仅覆盖春节期间。",
        ]
        assert all(statement in evidence["excerpt"] for statement in statements)
        assert all(item["generated_by"] == "evidence-text-baseline" for item in response.json())


def test_cross_place_evidence_is_rejected(tmp_path):
    with client_for(tmp_path) as client:
        first = client.post(
            "/places", json={"name": "Place A", "diagnostic_scope": "A"}
        ).json()
        second = client.post(
            "/places", json={"name": "Place B", "diagnostic_scope": "B"}
        ).json()

        evidence = client.post(
            "/evidence",
            json={
                "place_id": first["id"],
                "title": "Evidence for A",
                "source_type": "official",
                "excerpt": "Evidence belongs to Place A.",
            },
        ).json()

        response = client.post(
            "/findings",
            json={
                "place_id": second["id"],
                "statement": "This must not be allowed.",
                "dimension": "RESOURCE",
                "evidence_ids": [evidence["id"]],
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"]["message"] == "Evidence must belong to the same Place"


def test_cross_place_source_is_rejected(tmp_path):
    with client_for(tmp_path) as client:
        first = client.post(
            "/places", json={"name": "Place A", "diagnostic_scope": "A"}
        ).json()
        second = client.post(
            "/places", json={"name": "Place B", "diagnostic_scope": "B"}
        ).json()
        source = client.post(
            "/sources",
            json={"place_id": first["id"], "title": "A source", "source_type": "official"},
        ).json()

        response = client.post(
            "/evidence",
            json={
                "place_id": second["id"],
                "source_id": source["id"],
                "title": "Invalid evidence",
                "excerpt": "Must not cross places.",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "Source must belong to the same Place"


def test_edit_requires_human_revision(tmp_path):
    with client_for(tmp_path) as client:
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
                "excerpt": "A directly observable statement.",
            },
        ).json()
        finding = client.post(
            "/findings",
            json={
                "place_id": place["id"],
                "statement": "A directly observable statement.",
                "dimension": "RESOURCE",
                "evidence_ids": [evidence["id"]],
            },
        ).json()

        response = client.patch(
            f"/findings/{finding['id']}/verify",
            json={"status": "EDITED"},
        )
        assert response.status_code == 422
