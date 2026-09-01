# PlaceGap

**Evidence-backed diagnostics for cultural places.**

> Find where place value breaks. Show the evidence. Admit what you don't know.

PlaceGap is an open-source, local-first diagnostic workbench for cultural places, heritage sites, historic districts, rural destinations, and place-based projects.

Instead of generating another generic tourism strategy, PlaceGap structures source material into traceable evidence and reviewable findings, then uses those findings to test possible value-formation gaps and competing explanations.

## Why PlaceGap?

Most AI tools are good at producing answers. PlaceGap is designed to make a diagnosis **auditable**.

Its working chain is:

```text
Source → Evidence → Finding → Human Verification → Gap → Hypothesis
                                              ↘ Counter-evidence
                                              ↘ Missing evidence
                                              ↘ Alternative explanations
```

The first three layers have deliberately different jobs:

- **Source**: the whole document, webpage, interview, observation record, or other origin;
- **Evidence**: the excerpt, datum, or observation relevant to the current diagnostic scope;
- **Finding**: an atomic statement directly supportable by one or more Evidence items.

A Finding must not introduce a claim that is absent from its Evidence. Interpretation belongs later in Gap and Hypothesis work.

## Quick start for local testing

Requires Python 3.11+ and Node.js 22+.

```bash
git clone https://github.com/leepaean/placegap.git
cd placegap
bash scripts/dev.sh
```

Then open `http://127.0.0.1:5173` in a browser. The launcher creates the Python environment, installs dependencies when needed, starts the API and Vite UI, and stores local diagnostic state in `placegap.db`.

If you already cloned PlaceGap previously, update it before starting:

```bash
git pull
bash scripts/dev.sh
```

The launcher also reuses a local `certifi` CA bundle when available, which avoids a common macOS Python-framework TLS problem without disabling certificate verification.

## Source Packs

A Source Pack is a JSON bundle containing `sources[]` and `evidence[]`. Evidence entries refer to Sources through local `source_key` values, which PlaceGap resolves to durable Source IDs during import.

The repository contains a draft Qianfoyan / 千佛岩 pack at:

```text
examples/qianfoyan/source-pack.json
```

The pack contains Sources and Evidence only. It intentionally does not ship a pre-baked diagnosis.

## Finding proposals before LLM integration

The current `Draft from Evidence` action is deliberately conservative. It only splits Evidence text into verbatim candidate statements. It does not classify meaning, infer causes, or add facts.

This provider-free baseline gives future LLM integration a behavioral floor: an LLM must add useful structure while preserving evidence fidelity, uncertainty discipline, and traceability.

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

`v0.0.2-dev` — Source Library, persistent Source → Evidence provenance, Source Pack import, Evidence Board, and Finding Review are working locally.

LLM behavior remains intentionally deferred until this provenance workflow passes a second usability test with real material.

## Product principles

**Evidence before Advice.**  
**Hypothesis before Strategy.**  
**Unknown before Hallucination.**  
**Diagnosis before Intervention.**

## License

Apache License 2.0.
