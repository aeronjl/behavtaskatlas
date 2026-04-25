# Macaque RDM Confidence Wagering Slice

This vertical slice links the macaque RDM confidence/wagering protocol to the
Khalvati, Kiani, and Rao Nature Communications source-data ZIP for the
Kiani-Shadlen confidence task.

## Source Scope

The source used here is the article source-data ZIP, not a full raw behavioral
export. It contains CSVs for figure panels with motion strength, motion
duration, correctness, and sure-target choice for two monkeys. The adapter
pairs strength and duration CSVs row-by-row where the outcome column matches.

The slice emits source-row summaries for:

- no-sure-target accuracy by motion strength
- direction-choice accuracy when the sure target was available
- sure-target choice probability by motion strength

## Canonical Axis

The source CSVs do not preserve motion direction, signed coherence, direction
choice, raw session ids, or saccade response times. The slice therefore uses a
documented canonical convention:

- `stimulus_value` = absolute motion strength in percent coherence
- `stimulus_side` = unknown for nonzero strengths and none for zero strength
- `choice` = unknown
- source-specific confidence variables live in `task_variables`

The generated canonical table should be read as a source-data row table rather
than a deduplicated raw-trial table.

## Local Commands

```bash
uv run behavtaskatlas macaque-rdm-confidence-download
uv run behavtaskatlas macaque-rdm-confidence-harmonize
uv run behavtaskatlas macaque-rdm-confidence-analyze
uv run behavtaskatlas macaque-rdm-confidence-report
uv run behavtaskatlas site-index
```

Generated artifacts are written under:

```text
derived/macaque_rdm_confidence/khalvati-kiani-rao-natcomm2021-source-data/
```

Raw source downloads remain under ignored
`data/raw/macaque_rdm_confidence_khalvati/`.

## First Local Run

The first local run writes 174,160 canonical source rows, an accuracy summary,
a sure-target choice summary, an analysis JSON payload, dependency-free SVG
plots, and a static HTML report.
