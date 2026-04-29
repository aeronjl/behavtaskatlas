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
choice screen side, raw session ids, or saccade response times. The slice
therefore uses a documented canonical convention:

- `stimulus_value` = absolute motion strength in percent coherence
- direction-choice accuracy rows use `choice = right` for reported correct
  direction choices and `choice = left` for reported incorrect direction
  choices under a target-coded proxy
- sure-target-only rows keep `choice = unknown`; sure-target behavior remains
  in `task_variables.sure_target_chosen`
- `response_time` = source motion duration in seconds, flagged as a
  stimulus-duration proxy rather than raw saccade latency
- source-specific confidence variables live in `task_variables`

The generated canonical table should be read as a source-data row table rather
than a deduplicated raw-trial table. The target-coded choice and motion-duration
proxy unlock baseline psychometric and DDM fits, but they do not recover the
original signed direction or response-time semantics.

## Local Commands

```bash
uv run behavtaskatlas macaque-rdm-confidence-download
uv run behavtaskatlas macaque-rdm-confidence-harmonize
uv run behavtaskatlas macaque-rdm-confidence-analyze
uv run behavtaskatlas macaque-rdm-confidence-report
uv run behavtaskatlas macaque-rdm-confidence-intake-check
uv run behavtaskatlas site-index
```

Generated artifacts are written under:

```text
derived/macaque_rdm_confidence/khalvati-kiani-rao-natcomm2021-source-data/
```

Raw source downloads remain under ignored
`data/raw/macaque_rdm_confidence_khalvati/`.

## Raw Behavioral MATLAB Intake

The public POMDP-Confidence code references two raw/analyzed MATLAB behavior
files that are not in the public source-data ZIP:

```text
data/raw/macaque_rdm_confidence_khalvati/raw_behavior/
  beh_data.monkey1.mat
  beh_data.monkey2.mat
  redistribution_status.yaml
```

The intake preflight checks for both files, verifies that each MATLAB file has a
top-level `data` object, and inspects the positional columns used by the public
`Trial.readFile` code:

- position 1: coherence
- position 2: duration
- position 3: correct target
- position 4: choice target
- position 5: sure target shown

The sidecar `redistribution_status.yaml` must record:

```yaml
raw_files_received: YYYY-MM-DD
raw_files_redistributable: yes/no/unknown
derived_tables_redistributable: yes/no/unknown
license_notes: Summarize author terms before harmonizing.
```

Run the intake report after files are received:

```bash
uv run behavtaskatlas macaque-rdm-confidence-intake-check \
  --out-file derived/macaque_rdm_confidence/raw_behavior_intake.json
```

`macaque-rdm-confidence-raw-harmonize` is intentionally a guarded stub until
the requested MATLAB files pass this preflight. It fails with the same
actionable report when files or redistribution terms are missing.

## First Local Run

The first local run writes 174,160 canonical source rows, an accuracy summary,
a sure-target choice summary, an analysis JSON payload, dependency-free SVG
plots, and a static HTML report.
