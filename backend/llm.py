from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.models import Dimension, Evidence, Place


class LLMNotConfigured(RuntimeError):
    pass


class LLMProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str


@dataclass(frozen=True)
class LLMFindingProposal:
    statement: str
    dimension: Dimension
    evidence_ids: list[str]
    support_note: str | None = None


def get_llm_config() -> LLMConfig | None:
    api_key = (os.getenv("PLACEGAP_LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None

    base_url = (
        os.getenv("PLACEGAP_LLM_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).rstrip("/")
    model = (os.getenv("PLACEGAP_LLM_MODEL") or os.getenv("PLACEGAP_MODEL") or "gpt-5-mini").strip()
    return LLMConfig(api_key=api_key, base_url=base_url, model=model)


def llm_status() -> dict[str, Any]:
    config = get_llm_config()
    if config is None:
        return {
            "configured": False,
            "provider": "openai-compatible",
            "model": None,
            "mode": "evidence-text-baseline",
        }
    return {
        "configured": True,
        "provider": "openai-compatible",
        "model": config.model,
        "mode": "llm-evidence-bound",
    }


def _extract_json_object(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("LLM returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise LLMProviderError("LLM response must be a JSON object")
    return parsed


def _build_prompt(place: Place, evidence_items: list[Evidence]) -> str:
    evidence_payload = [
        {
            "id": str(item.id),
            "title": item.title,
            "kind": item.kind.value,
            "reliability": item.reliability.value,
            "suggested_scope": item.scope,
            "text": item.excerpt,
        }
        for item in evidence_items
    ]
    dimensions = [item.value for item in Dimension]

    return f"""You are the Finding layer of PlaceGap, an evidence-auditing workbench.

PLACE
Name: {place.name}
Diagnostic scope: {place.diagnostic_scope}

YOUR ONLY JOB
Produce a small set of atomic Findings that are directly supportable by the supplied Evidence.
A Finding is not a diagnosis, hypothesis, recommendation, causal explanation, or strategy.

STRICT RULES
1. Never add a factual claim that is absent from the Evidence.
2. Preserve time period, geography, attribution, uncertainty, and plan-vs-implementation status.
3. Do not turn a proposal, policy intention, or planned project into an implemented result.
4. Do not generalize holiday or sample data into annual or population-wide claims.
5. Low-reliability Evidence must remain clearly attributed or may be omitted.
6. Prefer diagnostically useful facts over trivia. Omit facts that do not help the stated diagnostic scope.
7. Merge duplicate or overlapping facts when doing so does not add a new claim.
8. Keep Findings atomic. One Finding should make one reviewable claim, though a tightly coupled numerical datum may stay together.
9. Suggest exactly one diagnostic dimension from this set: {dimensions}.
10. Every Finding must cite one or more Evidence IDs from the supplied set. Never invent an ID.
11. Return 5 to 12 Findings when the Evidence supports that many. Return fewer rather than padding.
12. support_note must briefly explain why the cited Evidence directly supports the Finding. It must not introduce a new factual claim.

OUTPUT
Return ONLY one JSON object in this exact shape:
{{
  "findings": [
    {{
      "statement": "...",
      "dimension": "RESOURCE",
      "evidence_ids": ["..."],
      "support_note": "..."
    }}
  ]
}}

EVIDENCE
{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}
"""


def _call_chat_completions(config: LLMConfig, prompt: str) -> str:
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": "Follow the PlaceGap evidence boundary strictly. Return JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:  # noqa: S310 - endpoint is user-configured intentionally
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMProviderError(f"LLM provider returned HTTP {exc.code}: {detail[:500]}") from exc
    except URLError as exc:
        raise LLMProviderError(f"Could not reach LLM provider: {exc.reason}") from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError("LLM provider response did not contain message content") from exc
    if not isinstance(content, str):
        raise LLMProviderError("LLM provider returned non-text message content")
    return content


def propose_findings_with_llm(place: Place, evidence_items: list[Evidence]) -> list[LLMFindingProposal]:
    config = get_llm_config()
    if config is None:
        raise LLMNotConfigured("No LLM API key is configured")

    allowed_ids = {str(item.id) for item in evidence_items}
    raw = _call_chat_completions(config, _build_prompt(place, evidence_items))
    parsed = _extract_json_object(raw)
    findings = parsed.get("findings")
    if not isinstance(findings, list):
        raise LLMProviderError("LLM JSON must contain findings[]")

    proposals: list[LLMFindingProposal] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for item in findings[:12]:
        if not isinstance(item, dict):
            raise LLMProviderError("Each finding must be an object")
        statement = item.get("statement")
        dimension_raw = item.get("dimension")
        evidence_ids = item.get("evidence_ids")
        support_note = item.get("support_note")
        if not isinstance(statement, str) or not statement.strip():
            raise LLMProviderError("Each finding needs a non-empty statement")
        try:
            dimension = Dimension(dimension_raw)
        except (TypeError, ValueError) as exc:
            raise LLMProviderError(f"Invalid finding dimension: {dimension_raw!r}") from exc
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise LLMProviderError("Each finding needs at least one evidence_id")
        normalized_ids = [str(value) for value in evidence_ids]
        unknown = sorted(set(normalized_ids) - allowed_ids)
        if unknown:
            raise LLMProviderError(f"LLM cited unknown Evidence IDs: {unknown}")
        key = (statement.strip(), tuple(sorted(set(normalized_ids))))
        if key in seen:
            continue
        seen.add(key)
        proposals.append(
            LLMFindingProposal(
                statement=statement.strip(),
                dimension=dimension,
                evidence_ids=list(dict.fromkeys(normalized_ids)),
                support_note=support_note.strip() if isinstance(support_note, str) and support_note.strip() else None,
            )
        )
    return proposals
