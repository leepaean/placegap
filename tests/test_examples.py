import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_qianfoyan_source_pack_imports_without_diagnosis(tmp_path):
    payload = json.loads((ROOT / "examples" / "qianfoyan" / "source-pack.json").read_text())

    with TestClient(create_app(tmp_path / "qianfoyan.db")) as client:
        place = client.post(
            "/places",
            json={
                "name": "Qianfoyan / 千佛岩",
                "place_type": "heritage attraction",
                "diagnostic_scope": "Identify structural breaks in resource-to-place-value formation without assuming a traffic problem.",
            },
        ).json()

        imported = client.post(
            f"/places/{place['id']}/source-packs/import",
            json=payload,
        )
        assert imported.status_code == 201
        assert imported.json() == {"sources_created": 8, "evidence_created": 10}

        state = client.get(f"/places/{place['id']}/diagnostic-state").json()
        assert len(state["sources"]) == 8
        assert len(state["evidence"]) == 10
        assert state["findings"] == []
        assert state["hypotheses"] == []

        # A Source Pack supplies provenance and Evidence, not a pre-baked diagnosis.
        assert all(item["source_id"] for item in state["evidence"])
        assert {item["kind"] for item in state["evidence"]} == {"DATUM", "SUMMARY"}
