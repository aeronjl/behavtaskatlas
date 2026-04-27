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

The slice operates on a Visual Behavior behavior NWB file. Obtain one via the
Allen SDK in a separate environment, AWS CLI (`aws s3 cp s3://visual-behavior-ophys-data/...`),
or the `allen-visual-behavior-download` helper if a public HTTPS URL is known.

```bash
uv sync --extra allen
uv run --extra allen behavtaskatlas allen-visual-behavior-download \
  --nwb-url https://visual-behavior-ophys-data.s3.amazonaws.com/<key>.nwb \
  --out-file data/raw/allen_visual_behavior/behavior_session.nwb
uv run --extra allen behavtaskatlas allen-visual-behavior-harmonize \
  --nwb-file data/raw/allen_visual_behavior/behavior_session.nwb
uv run behavtaskatlas allen-visual-behavior-analyze
uv run behavtaskatlas allen-visual-behavior-report
uv run behavtaskatlas site-index
```

By default this writes ignored local artifacts under:

```text
derived/allen_visual_behavior/
```

The downloaded NWB file lives under `data/raw/allen_visual_behavior/`, which
is also gitignored. The resolved `behavior_session_id`, NWB SHA-256, and byte
size are recorded in `provenance.json`.

## Data Policy

Allen Brain Observatory data are released under the Allen Institute Terms of
Use for research and educational use with attribution. The cache directory and
all derived artifacts stay under ignored local storage until release policy is
confirmed.

## Open Questions

1. Pin a canonical default `behavior_session_id` in the slice manifest after
   first successful run, mirroring how the IBL slice pins one OpenAlyx eid.
2. Decide whether to filter or retain `auto_rewarded` trials in the canonical
   table by default.
3. Add a multi-session aggregate (subject-level pooling) once the single-
   session slice is verified.
