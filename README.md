# PlaceGap

**Evidence-backed diagnostics for cultural places.**

> Find where place value breaks. Show the evidence. Admit what you don't know.

PlaceGap is an open-source, local-first diagnostic workbench for cultural places, heritage sites, historic districts, rural destinations, and place-based projects.

Instead of generating another generic tourism strategy, PlaceGap structures evidence into findings, identifies possible value-formation gaps, tests competing explanations, and makes uncertainty explicit.

## Why PlaceGap?

Most AI tools are good at producing answers. PlaceGap is designed to make a diagnosis **auditable**.

Its core chain is:

```text
Evidence → Finding → Human Verification → Gap → Hypothesis
                                      ↘ Counter-evidence
                                      ↘ Missing evidence
                                      ↘ Alternative explanations
```

PlaceGap deliberately separates:

- what a source directly supports;
- what a human or model infers;
- what contradicts a hypothesis;
- what remains unknown.

## Diagnostic dimensions

PlaceGap uses eight diagnostic dimensions as coordinates, not as a rigid causal law:

1. `RESOURCE`
2. `MEANING`
3. `VISIBILITY`
4. `EXPERIENCE`
5. `PRODUCT`
6. `CONVERSION`
7. `ADVOCACY`
8. `REGENERATION`

The product is interested in the **gaps between them**, not in producing pseudo-precise scores.

## Development status

`v0.0.1` — repository bootstrap and core domain schema.

The first vertical slice is:

```text
Evidence → Finding → Human Verify → Hypothesis
```

## Product principles

**Evidence before Advice.**  
**Hypothesis before Strategy.**  
**Unknown before Hallucination.**  
**Diagnosis before Intervention.**

## License

Apache License 2.0.
