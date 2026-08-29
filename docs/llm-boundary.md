# LLM Boundary

PlaceGap should not make an LLM the source of truth.

Allowed model roles in v0.1:

1. propose atomic Findings from Evidence;
2. propose Gap candidates from accepted Findings;
3. propose Hypotheses with support, contradiction, missing evidence, and alternatives;
4. audit a diagnostic state for unsupported claims or overconfidence.

Model output remains a proposal until accepted by a human reviewer.

The system must remain useful for manually created Evidence, Findings, and Hypotheses even when no LLM is configured.
