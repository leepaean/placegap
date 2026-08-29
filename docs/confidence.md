# Confidence Rules

PlaceGap v0.1 prohibits fake precision.

Allowed confidence states:

- HIGH
- MEDIUM
- LOW
- UNKNOWN

## Suggested interpretation

### HIGH
Multiple independent sources across source types support the hypothesis and no strong contradiction is present.

### MEDIUM
More than one source supports the hypothesis, but representativeness, scope, or contradiction remains materially uncertain.

### LOW
Support is narrow, indirect, single-source, or strongly contested.

### UNKNOWN
Current evidence is insufficient for a directional diagnosis.

A model may propose confidence. A human reviewer owns the accepted state.
