# Rodgers Whisker Object Recognition Slice

This slice turns one Rodgers DANDI NWB session, or a CSV/TSV export of its NWB
trials table, into an adapter-backed workflow for tactile object recognition in
head-fixed mice.

## Scope

- Protocol record: `protocol.mouse-whisker-object-recognition-lick`
- Dataset record: `dataset.rodgers-whisker-object-recognition-dandi`
- Source: DANDI dandiset `000231`, version `0.220904.1554`
- Paper reference: Rodgers, Scientific Data, 2022
- Local source input: a DANDI NWB session file or an exported trials table with
  the same NWB trial columns

## Operational Mapping

The adapter preserves the source task variables rather than forcing a scalar
tactile evidence axis:

- `stimulus`: concave, convex, or nothing/catch condition
- `servo_position`: close, medium, or far object position
- `choice`: left/right lick choice; nogo/spoil maps to no-response
- `outcome`: correct, error, or spoil
- `rewarded_side`: correct lick side for the current rule
- `ignore_trial`: source analysis-exclusion flag retained in canonical rows
- `response_window_open_time` and `choice_time`: used to compute response
  latency
- `processing/identified_whisker_contacts` tables: optional contact counts by
  whisker when present

Shape-discrimination and shape-detection rows are kept under an explicit
`task_rule` because the same shape labels have different action mappings across
rules.

## Local Workflow

Download a session NWB file through DANDI outside version control, then run:

```bash
uv run --extra nwb behavtaskatlas rodgers-harmonize \
  --source-file data/raw/rodgers_whisker_object_recognition/rodgers_session.nwb
uv run behavtaskatlas rodgers-analyze
uv run behavtaskatlas rodgers-report
uv run behavtaskatlas site-index
```

For a lightweight trials-table export:

```bash
uv run behavtaskatlas rodgers-harmonize \
  --source-file data/raw/rodgers_whisker_object_recognition/rodgers_trials.csv \
  --subject-id KM91
```

Generated artifacts are written under:

```text
derived/rodgers_whisker_object_recognition/rodgers-whisker-object-recognition-dandi/
```

The complete DANDI release includes large NWB and video assets, so raw source
files remain in ignored local storage.
