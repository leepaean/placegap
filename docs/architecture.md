# Architecture Notes

PlaceGap is local-first and intentionally simple in v0.1.

## Planned layers

- `core/`: domain objects and diagnostic rules
- `backend/`: FastAPI application and persistence
- `frontend/`: evidence and hypothesis workbench
- `examples/`: controlled validation cases
- `docs/`: methodology and evaluation protocol

## Design constraint

The domain model must survive UI replacement. PlaceGap's durable OSS asset is the diagnostic protocol, not a particular frontend.

## Persistence

SQLite is the v0.1 target. The current bootstrap may use in-memory stores while API contracts are stabilized.

## AI boundary

LLMs may propose Findings, Gaps, Hypotheses, missing evidence, and alternative explanations. Humans own verification and final diagnostic state.
