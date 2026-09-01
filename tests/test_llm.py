import json

from fastapi.testclient import TestClient

import backend.llm as llm_module
from backend.main import create_app


def test_llm_status_is_baseline_without_key(tmp_path, monkeypatch):
    monkeypatch.delenv("PLACEGAP_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with TestClient(create_app(tmp_path / "status.db")) as client:
        response = client.get("/llm/status")
        assert response.status_code == 200
        assert response.json()["configured"] is False
        assert response.json()["mode"] == "evidence-text-baseline"


def test_llm_proposals_filter_and_suggest_dimension(tmp_path, monkeypatch):
    monkeypatch.setenv("PLACEGAP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("PLACEGAP_LLM_MODEL", "test-model")

    with TestClient(create_app(tmp_path / "llm.db")) as client:
        place = client.post(
            "/places",
            json={
                "name": "Qianfoyan",
                "diagnostic_scope": "Identify structural breaks without assuming a traffic problem.",
            },
        ).json()
        evidence = client.post(
            "/evidence",
            json={
                "place_id": place["id"],
                "title": "Holiday traffic",
                "excerpt": "During May Day, Qianfoyan received 81,300 visits, up 9.61% year on year.",
                "kind": "DATUM",
                "scope": "VISIBILITY",
                "reliability": "HIGH",
            },
        ).json()

        provider_response = {
            "findings": [
                {
                    "statement": "During the 2025 May Day period, Qianfoyan received 81,300 visits, up 9.61% year on year.",
                    "dimension": "VISIBILITY",
                    "evidence_ids": [evidence["id"]],
                    "support_note": "The linked datum directly reports the visitor count and year-on-year change.",
                }
            ]
        }
        monkeypatch.setattr(
            llm_module,
            "_call_chat_completions",
            lambda config, prompt: json.dumps(provider_response),
        )

        response = client.post(
            f"/places/{place['id']}/finding-proposals",
            json={"evidence_ids": [evidence["id"]]},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["dimension"] == "VISIBILITY"
        assert body[0]["generated_by"] == "llm:test-model"
        assert body[0]["evidence_ids"] == [evidence["id"]]
        assert "visitor count" in body[0]["support_note"]


def test_llm_cannot_cite_unknown_evidence_id(tmp_path, monkeypatch):
    monkeypatch.setenv("PLACEGAP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("PLACEGAP_LLM_MODEL", "test-model")

    with TestClient(create_app(tmp_path / "unknown.db")) as client:
        place = client.post(
            "/places",
            json={"name": "Place", "diagnostic_scope": "Boundary test"},
        ).json()
        evidence = client.post(
            "/evidence",
            json={
                "place_id": place["id"],
                "title": "Known evidence",
                "excerpt": "A known fact.",
            },
        ).json()

        monkeypatch.setattr(
            llm_module,
            "_call_chat_completions",
            lambda config, prompt: json.dumps(
                {
                    "findings": [
                        {
                            "statement": "A known fact.",
                            "dimension": "RESOURCE",
                            "evidence_ids": ["00000000-0000-0000-0000-000000000001"],
                            "support_note": "Invalid citation for test.",
                        }
                    ]
                }
            ),
        )

        response = client.post(
            f"/places/{place['id']}/finding-proposals",
            json={"evidence_ids": [evidence["id"]]},
        )
        assert response.status_code == 502
        assert "unknown Evidence IDs" in response.json()["detail"]
