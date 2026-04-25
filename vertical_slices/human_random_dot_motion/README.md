# Human Random-Dot Motion Slice

This vertical slice makes the human RDM reaction-time protocol report-backed
using the CoSMo2017 distribution of Palmer, Huk, and Shadlen Experiment 1.

## Source Protocol

- Protocol record: `protocol.human-rdm-button-reaction-time`
- Dataset record: `dataset.palmer-huk-shadlen-human-rdm-cosmo2017`
- Source repository: `DrugowitschLab/CoSMo2017`
- Pinned commit: `5fbffc45adea2e7e30407a33931e39fb84219c83`
- Source files: `phs_ah.mat`, `phs_eh.mat`, `phs_jd.mat`, `phs_jp.mat`,
  `phs_mk.mat`, and `phs_mm.mat`

## Source Fields

The adapter uses the CoSMo2017 PHS MATLAB fields:

- `rt`: reaction time in seconds.
- `choice`: response code, with `0` left and `1` right.
- `cohs`: signed motion coherence, with rightward motion positive and leftward
  motion negative.

## Current Interpretation

CoSMo2017 already removes bad trials, combines coherence and direction into
signed coherence, converts reaction times to seconds, and assigns random
choices to zero-coherence trials. The slice preserves those choices and follows
the CoSMo2017 fitting script convention that treats zero coherence as rightward
when reconstructing correctness.

## Local Regeneration

```bash
uv run --extra rdm behavtaskatlas human-rdm-download
uv run --extra rdm behavtaskatlas human-rdm-harmonize
uv run behavtaskatlas human-rdm-analyze
uv run behavtaskatlas human-rdm-report
uv run behavtaskatlas site-index
```

By default this writes ignored raw data under:

```text
data/raw/human_random_dot_motion/palmer_huk_shadlen/
```

and ignored local artifacts under:

```text
derived/human_random_dot_motion/palmer-huk-shadlen-cosmo2017/
```
