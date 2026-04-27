# Allen Visual Behavior Slice

This vertical slice maps a single Allen Brain Observatory Visual Behavior
session into the canonical trial model. It is the first non-2AFC, non-evidence-
accumulation slice in `behavtaskatlas`, and the first to exercise go/no-go
choice values in `CanonicalTrial`.

## Source Protocol

- Family record: `family.visual-change-detection`
- Protocol record: `protocol.mouse-visual-change-detection-allen`
- Dataset record: `dataset.allen-brain-observatory-visual-behavior`
- Source archive: Allen Brain Observatory Visual Behavior 2P AWS Open Data bucket
- Access: direct h5py read of the NWB file (avoids the `allensdk` dep, which
  pins `scipy<1.11` and conflicts with the other extras)

## Source Fields

The adapter reads the trials DataFrame from `BehaviorSession.trials`. Required
columns are `go`, `catch`, `hit`, `miss`, `false_alarm`, `correct_reject`,
`aborted`, `auto_rewarded`, `initial_image_name`, `change_image_name`,
`response_latency`, and `reward_volume`. Optional columns are
`change_time_no_display_delay`, `trial_length`, `lick_times`, `reward_time`,
and `session_type`.

## Canonical Mapping

| Canonical field | Source |
| --- | --- |
| `stimulus_value` | not used; image change is categorical |
| `stimulus_side` | always `none` |
| `evidence_strength` | not used; categorical change |
| `choice` | lick → `go`, withhold → `withhold`, early lick → `no-response` |
| `correct` | `True` for hit and correct rejection, `False` for miss and false alarm |
| `response_time` | `response_latency` seconds after change |
| `feedback` | `reward` for hits and auto-rewarded with positive volume, otherwise `none` |
| `reward` | `reward_volume` in mL |
| `task_variables.outcome` | hit, miss, false_alarm, correct_reject, aborted, auto_rewarded |
| `task_variables.image_pair` | `initial_image_name`->`change_image_name` |

## Current Implementation

- Adapter: `src/behavtaskatlas/allen.py`
- Tests: `tests/test_allen.py`
- Dataset metadata: `datasets/allen-brain-observatory-visual-behavior.yaml`

## Local Regeneration Command

The canonical session for this slice is `behavior_session_id 899390684`
(mouse `453911`, `OPHYS_1_images_A`, project `VisualBehaviorMultiscope`). It is
served as a public NWB file from the Allen `visual-behavior-ophys-data` S3
bucket. Sister sessions can be substituted by changing `--nwb-url` and
`--nwb-file`.

```bash
uv sync --extra allen
uv run --extra allen behavtaskatlas allen-visual-behavior-download \
  --nwb-url https://visual-behavior-ophys-data.s3.amazonaws.com/visual-behavior-ophys/behavior_sessions/behavior_session_899390684.nwb \
  --out-file data/raw/allen_visual_behavior/behavior_session_899390684.nwb
uv run --extra allen behavtaskatlas allen-visual-behavior-harmonize \
  --nwb-file data/raw/allen_visual_behavior/behavior_session_899390684.nwb
uv run behavtaskatlas allen-visual-behavior-analyze
uv run behavtaskatlas allen-visual-behavior-report
uv run behavtaskatlas site-index
```

By default this writes ignored local artifacts under:

```text
derived/allen_visual_behavior/
```

The downloaded NWB file lives under `data/raw/allen_visual_behavior/`, which
is also gitignored. The resolved `behavior_session_id`, NWB SHA-256, byte
size, and session UUID are recorded in `provenance.json`.

Verified local run on `behavior_session_899390684.nwb`:

- 654 trials harmonized; outcome counts: hit 180, miss 56, false_alarm 3,
  correct_reject 31, aborted 379, auto_rewarded 5
- Hit rate 0.76, false-alarm rate 0.09, d-prime 1.99 (matches the
  `behavior_session_table.csv` per-session counts)
- 56 distinct image pairs in the per-pair table
- Median hit lick latency ~396 ms after change

The Allen `behavior_session_table.csv` is published alongside the bucket at
`s3://visual-behavior-ophys-data/visual-behavior-ophys/project_metadata/behavior_session_table.csv`
and can be used to filter for other Familiar/OPHYS sessions.

## Data Policy

Allen Brain Observatory data are released under the Allen Institute Terms of
Use for research and educational use with attribution. The cache directory and
all derived artifacts stay under ignored local storage until release policy is
confirmed.

## Open Questions

1. Decide whether to filter or retain `auto_rewarded` trials in the canonical
   table by default.
2. Add a multi-session aggregate (subject-level pooling) once the single-
   session slice has had its first cross-session sanity check.
3. Consider switching the slice to a fully-trained `OPHYS_4` or later session
   if a higher hit-rate / lower abort-rate exemplar is preferred.
