# Random-Dot Motion Slice

This is the third vertical slice for `behavtaskatlas`.

## Goal

Add a classic macaque random-dot motion task so the MVP compares visual contrast,
auditory click accumulation, and motion-coherence decision tasks with the same
canonical trial and report surface.

## Source Protocol

- Protocol record: `protocol.random-dot-motion-classic-macaque`
- Dataset record: `dataset.roitman-shadlen-rdm-pyddm`
- Source data access: processed Roitman-Shadlen CSV distributed with PyDDM
- Pinned PyDDM commit: `cf161c11e8f99f18cf805a7ae1da8623faddad86`

## Source Fields

The first adapter targets the processed PyDDM CSV:

- `monkey`: macaque identifier.
- `rt`: reaction time in seconds.
- `coh`: unsigned motion coherence as a fraction.
- `correct`: `1` correct, `0` incorrect.
- `trgchoice`: chosen target identity.

The PyDDM extraction script derives the CSV from the original Roitman-Shadlen
data by computing `rt` from saccade time minus stimulus onset, scaling coherence
to a fraction, and retaining monkey id, correctness, and target choice.

## Canonical Mapping

| Canonical field | Source |
| --- | --- |
| `subject_id` | `monkey` formatted as `monkey-{id}` |
| `session_id` | fixed processed dataset id `roitman-shadlen-pyddm` |
| `stimulus_value` | reconstructed signed coherence percentage, target 1 positive |
| `stimulus_side` | target 1/right, target 2/left as a canonical convention |
| `evidence_strength` | absolute coherence percentage |
| `choice` | `trgchoice`: target 1/right, target 2/left |
| `correct` | `correct`: `1` true, `0` false |
| `response_time` | `rt` in seconds |
| `feedback` | `correct` mapped to reward/error |
| `task_variables.coherence_fraction` | `coh` |
| `task_variables.signed_coherence_fraction_target1_positive` | reconstructed signed coherence fraction |
| `task_variables.target_choice` | `trgchoice` |

Signed coherence is reconstructed from unsigned coherence, target choice, and
correctness. Target 1 trials are positive when correct and negative when
incorrect; target 2 trials are negative when correct and positive when
incorrect.

## Current Implementation

- Adapter and report code: `src/behavtaskatlas/rdm.py`
- CLI commands: `rdm-download`, `rdm-harmonize`, `rdm-analyze`, `rdm-report`
- Tests: `tests/test_rdm.py`
- Dataset metadata: `datasets/roitman-shadlen-rdm-pyddm.yaml`
- Analysis metadata: `analyses/random_dot_motion.yaml`
- Source-field mapping: `vertical_slices/random_dot_motion/source_fields.yaml`

## Local Regeneration Command

Download the processed CSV under ignored local raw-data storage:

```bash
uv run behavtaskatlas rdm-download
```

Then regenerate the slice:

```bash
uv run behavtaskatlas rdm-harmonize
uv run behavtaskatlas rdm-analyze
uv run behavtaskatlas rdm-report
uv run behavtaskatlas site-index
```

By default this writes ignored local artifacts under:

```text
derived/random_dot_motion/roitman-shadlen-pyddm/
```

Verified local run:

- Downloaded CSV size: 132,610 bytes.
- Downloaded CSV SHA256: `7ac2daa16e9631aa189ae146a89f9f29cc6fccd6c0f31b4d5849990a6cebbd4b`.
- Canonical trials: 6,149.
- Subjects: `monkey-1`, `monkey-2`.
- Psychometric summary rows: 11 signed-coherence rows.
- Chronometric summary rows: 6 absolute-coherence rows.
- Static report: `derived/random_dot_motion/roitman-shadlen-pyddm/report.html`.
- Static index: `derived/index.html`, now indexing three report-available slices.

The chronometric summary shows the expected pattern for this task: median
reaction time falls as absolute motion coherence rises, from about 0.82 s at
0% coherence to about 0.41 s at 51.2% coherence. Accuracy rises from near
chance at 0% coherence to 1.0 at 51.2% coherence.

## Caveats

- The processed CSV does not preserve original session labels.
- Target 1 and target 2 are mapped onto canonical right/left labels for
  comparability, not because stable screen side is known.
- The adapter keeps all downloaded rows; DDM-compatible filtering for very short
  or long reaction times is deferred.
- PyDDM is MIT licensed, but the original Roitman-Shadlen data redistribution
  terms should be confirmed before committing derived trial tables.

## Next Steps

1. Add per-monkey psychometric and chronometric splits.
2. Add a DDM-oriented fit path, probably using PyDDM or a lightweight pinned
   equivalent.
3. Confirm whether the original MATLAB files expose stable target-position or
   session-level metadata that should replace the processed CSV convention.
