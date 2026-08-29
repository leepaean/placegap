# Contributing to PlaceGap

Thank you for helping test whether evidence-backed place diagnosis deserves to exist as software.

## What we value

Contributions should improve at least one of these properties:

- traceability;
- uncertainty discipline;
- contradiction handling;
- separation of fact from inference;
- reproducibility of a diagnosis;
- useful diagnostic structure.

## What we are not optimizing for yet

Please avoid adding:

- automatic strategy generation;
- destination marketing copy;
- social-media scraping;
- numerical place scoring;
- multi-agent orchestration;
- large dashboards.

These are intentionally outside v0.1.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Pull requests

Keep PRs narrow. Explain:

1. what diagnostic failure the change fixes;
2. how it is tested;
3. whether it changes the domain schema;
4. whether it risks turning inference into fact.

## Domain language

Use these terms consistently:

- Evidence
- Finding
- Gap
- Hypothesis
- Evidence Need
- Alternative Explanation
- Contradicting Evidence

A Finding must be directly supportable by Evidence. A Hypothesis is an interpretation and must never be silently promoted to fact.
