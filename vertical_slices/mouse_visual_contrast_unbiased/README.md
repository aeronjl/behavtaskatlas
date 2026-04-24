# Mouse Visual Contrast Training Slice

This vertical slice makes the catalog-only mouse visual contrast wheel protocol report-backed using one public IBL trainingChoiceWorld session.

## Source Protocol

- Protocol record: `protocol.mouse-visual-contrast-wheel-unbiased`
- Dataset record: `dataset.ibl-public-behavior`
- OpenAlyx session: `6a6442d1-dd7d-4717-b7b1-5874aefbd6fc`
- Subject: `KS014`
- Lab: `cortexlab`
- Task protocol: `_iblrig_tasks_trainingChoiceWorld5.2.9`

## Source Fields

The adapter reuses the IBL trials table schema:

- `contrastLeft`: left stimulus contrast when present.
- `contrastRight`: right stimulus contrast when present.
- `choice`: IBL choice code, with `1` left, `-1` right, and `0` no-response.
- `feedbackType`: outcome code.
- `response_times`: response timestamp.
- `stimOn_times`: stimulus onset timestamp.
- `probabilityLeft`: source task context, preserved as `prior_context`.
- `rewardVolume`: optional reward amount.

## Current Interpretation

The session is a trainingChoiceWorld session, not the existing biased/ephys visual decision slice. The source `probabilityLeft` values vary during training, so this slice preserves them as context but does not interpret them as a controlled block-prior manipulation.

## Local Regeneration

```bash
uv run --extra ibl behavtaskatlas mouse-unbiased-harmonize \
  --cache-dir data/raw/openalyx-cache
uv run behavtaskatlas mouse-unbiased-analyze
uv run behavtaskatlas mouse-unbiased-report
uv run behavtaskatlas site-index
```

By default this writes ignored local artifacts under:

```text
derived/mouse_visual_contrast_unbiased/6a6442d1-dd7d-4717-b7b1-5874aefbd6fc/
```
