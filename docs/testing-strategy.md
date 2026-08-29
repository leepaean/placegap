# Testing Strategy

## Unit tests

Validate domain rules such as:

- Findings retain Evidence references.
- Confidence remains qualitative.
- Human verification states are explicit.
- Hypotheses can contain both supporting and contradicting evidence.

## API tests

Validate the full vertical slice:

`Place → Evidence → Finding → Human Verify → Hypothesis → Diagnostic State`

## Product tests

Code correctness is insufficient. PlaceGap must later pass the blind comparison defined in `evaluation.md`.
