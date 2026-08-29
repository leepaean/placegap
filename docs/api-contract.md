# API Contract Principles

The first API exists to validate the domain model, not to stabilize a public SDK.

Rules:

- Unknown IDs return explicit HTTP 404 responses.
- Invalid cross-place references return 422/400-class errors rather than server exceptions.
- Creating a Finding requires existing Evidence from the same Place.
- Creating a Hypothesis requires referenced Evidence from the same Place.
- Human verification is an explicit mutation, not an implicit model action.
- Rejected diagnostic objects remain auditable.
