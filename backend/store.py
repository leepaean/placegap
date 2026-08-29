from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from core.models import Evidence, EvidenceNeed, Finding, Gap, Hypothesis, Place

ModelT = TypeVar("ModelT", bound=BaseModel)

_TABLE_MODELS = {
    "places": Place,
    "evidence": Evidence,
    "findings": Finding,
    "gaps": Gap,
    "hypotheses": Hypothesis,
    "evidence_needs": EvidenceNeed,
}


class SQLiteStore:
    """Durable local persistence for the evolving v0.1 domain schema."""

    def __init__(self, path: str | Path = "placegap.db") -> None:
        self.path = str(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS places (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY,
                    place_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(place_id) REFERENCES places(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_evidence_place ON evidence(place_id);

                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY,
                    place_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(place_id) REFERENCES places(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_findings_place ON findings(place_id);

                CREATE TABLE IF NOT EXISTS gaps (
                    id TEXT PRIMARY KEY,
                    place_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(place_id) REFERENCES places(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_gaps_place ON gaps(place_id);

                CREATE TABLE IF NOT EXISTS hypotheses (
                    id TEXT PRIMARY KEY,
                    place_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(place_id) REFERENCES places(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_hypotheses_place ON hypotheses(place_id);

                CREATE TABLE IF NOT EXISTS evidence_needs (
                    id TEXT PRIMARY KEY,
                    place_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(place_id) REFERENCES places(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_evidence_needs_place ON evidence_needs(place_id);
                """
            )

    def _put(self, table: str, model: BaseModel, place_id: str | None = None) -> None:
        if table not in _TABLE_MODELS:
            raise ValueError(f"Unsupported table: {table}")
        columns = "id, payload" if table == "places" else "id, place_id, payload"
        placeholders = "?, ?" if table == "places" else "?, ?, ?"
        values = (
            (str(model.id), model.model_dump_json())
            if table == "places"
            else (str(model.id), place_id, model.model_dump_json())
        )
        with self.connect() as connection:
            connection.execute(
                f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
                values,
            )

    def _get(self, table: str, entity_id: str) -> BaseModel | None:
        model_type = _TABLE_MODELS[table]
        with self.connect() as connection:
            row = connection.execute(
                f"SELECT payload FROM {table} WHERE id = ?", (entity_id,)
            ).fetchone()
        return None if row is None else model_type.model_validate_json(row["payload"])

    def _list_for_place(self, table: str, place_id: str) -> list[BaseModel]:
        model_type = _TABLE_MODELS[table]
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT payload FROM {table} WHERE place_id = ? ORDER BY rowid",
                (place_id,),
            ).fetchall()
        return [model_type.model_validate_json(row["payload"]) for row in rows]

    def put_place(self, place: Place) -> None:
        self._put("places", place)

    def get_place(self, place_id: str) -> Place | None:
        return self._get("places", place_id)  # type: ignore[return-value]

    def list_places(self) -> list[Place]:
        with self.connect() as connection:
            rows = connection.execute("SELECT payload FROM places ORDER BY rowid DESC").fetchall()
        return [Place.model_validate_json(row["payload"]) for row in rows]

    def put_evidence(self, evidence: Evidence) -> None:
        self._put("evidence", evidence, str(evidence.place_id))

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        return self._get("evidence", evidence_id)  # type: ignore[return-value]

    def list_evidence(self, place_id: str) -> list[Evidence]:
        return self._list_for_place("evidence", place_id)  # type: ignore[return-value]

    def put_finding(self, finding: Finding) -> None:
        self._put("findings", finding, str(finding.place_id))

    def get_finding(self, finding_id: str) -> Finding | None:
        return self._get("findings", finding_id)  # type: ignore[return-value]

    def list_findings(self, place_id: str) -> list[Finding]:
        return self._list_for_place("findings", place_id)  # type: ignore[return-value]

    def put_gap(self, gap: Gap) -> None:
        self._put("gaps", gap, str(gap.place_id))

    def get_gap(self, gap_id: str) -> Gap | None:
        return self._get("gaps", gap_id)  # type: ignore[return-value]

    def list_gaps(self, place_id: str) -> list[Gap]:
        return self._list_for_place("gaps", place_id)  # type: ignore[return-value]

    def put_hypothesis(self, hypothesis: Hypothesis) -> None:
        self._put("hypotheses", hypothesis, str(hypothesis.place_id))

    def get_hypothesis(self, hypothesis_id: str) -> Hypothesis | None:
        return self._get("hypotheses", hypothesis_id)  # type: ignore[return-value]

    def list_hypotheses(self, place_id: str) -> list[Hypothesis]:
        return self._list_for_place("hypotheses", place_id)  # type: ignore[return-value]

    def put_evidence_need(self, evidence_need: EvidenceNeed) -> None:
        self._put("evidence_needs", evidence_need, str(evidence_need.place_id))

    def list_evidence_needs(self, place_id: str) -> list[EvidenceNeed]:
        return self._list_for_place("evidence_needs", place_id)  # type: ignore[return-value]
