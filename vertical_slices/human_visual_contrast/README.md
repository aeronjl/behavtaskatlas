# Human Visual Contrast Prior-Cue Slice

This slice links the human visual contrast 2AFC protocol to Walsh et al.'s OSF
dataset for a contrast-discrimination EEG/SSVEP task with neutral, valid, and
invalid probabilistic cues.

The source used here is the processed OSF behavioural stats matrix
`1. Behavioural Analysis.mat`, backed by the published `Behavioural_Analysis.m`
and `Experiment_Task.m` scripts. The matrix has 66,200 rows from 12 observers.
Each row contains response time, correctness, cue, pulse type, exposure bin,
subject code, lower-frequency response, session-titrated difficulty, and reward.

## Canonical Axis

The processed stats matrix does not preserve the original left/right tilt
response. It does preserve whether the participant responded to the lower or
higher flicker-frequency grating. The slice therefore uses a documented
canonical convention:

- canonical `right` = lower-frequency response or target
- canonical `left` = higher-frequency response or target
- signed contrast = target-minus-distractor contrast percentage points
- positive signed contrast = lower-frequency grating was the target

The adapter reconstructs target frequency from correctness and the
lower-frequency response flag. The convention is preserved in
`task_variables` on every canonical trial.

## Local Commands

```bash
uv sync --extra visual
uv run --extra visual behavtaskatlas human-visual-download
uv run --extra visual behavtaskatlas human-visual-harmonize
uv run behavtaskatlas human-visual-analyze
uv run behavtaskatlas human-visual-report
uv run behavtaskatlas site-index
```

Generated artifacts are written under:

```text
derived/human_visual_contrast/walsh-prior-cue-human-contrast-osf/
```

Raw OSF downloads remain under ignored `data/raw/human_visual_contrast_walsh/`.

## First Local Run

The first local run writes 66,200 canonical trials, cue-split psychometric
summary rows, an analysis JSON payload, a dependency-free SVG psychometric plot,
and a static HTML report.
