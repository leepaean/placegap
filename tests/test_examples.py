import json
from pathlib import Path

from core.models import Evidence


def test_qianfoyan_evidence_pack_matches_domain_schema():
    path = Path("examples/qianfoyan/evidence.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    evidence = [Evidence.model_validate(item) for item in data]
    assert len(evidence) >= 10
    assert len({item.place_id for item in evidence}) == 1
    assert any(item.reliability.value == "LOW" for item in evidence)
    assert any(item.scope == "CONVERSION" for item in evidence)
