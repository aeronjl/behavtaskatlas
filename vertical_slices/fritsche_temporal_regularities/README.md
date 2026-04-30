# Fritsche Temporal Regularities Slice

This vertical slice adds a behavior-first adapter for the Fritsche et al. mouse
visual decision dataset. The source task is a strict wheel 2AFC visual contrast
task, but the experiment manipulates stimulus-side sequence statistics across
Neutral, Repeating, and Alternating environments.

## Source Protocol

- Protocol record: `protocol.mouse-visual-contrast-wheel-temporal-regularities`
- Dataset record: `dataset.fritsche-temporal-regularities-figshare`
- Source DOI: `10.6084/m9.figshare.24179829.v2`
- Article DOI: `10.1038/s41467-024-51393-8`

## Source Fields

The adapter reads generated behavior CSVs inside Figshare `data.zip`:

- `data/data_exp1_transitional_regularities.csv`
- `data/data_exp2_adaptation_test.csv`
- `data/data_exp3_photometry_behavior.csv`

Core fields are `mouseName`, `expRef`, `trialNumber`, `contrastLeft`,
`contrastRight`, `correctResponse`, `choice`, `feedback`, `environment`, and
`stimulusOnsetTime`. Optional timing, reward, altitude, exclusion, and
choice-history helper columns are preserved in canonical `task_variables`.

## Current Interpretation

The atlas treats Neutral, Repeating, and Alternating as task environments,
not as inferred cognitive states. Source `NoGo` rows are mapped to canonical
`no-response` because they are rare timeout/no-turn outcomes in a left/right
wheel task, not a rewarded third choice as in Steinmetz/Zatka-Haas unforced
tasks.

The analysis now includes lag-1 operational summaries computed within each
source session: stimulus-side transitions, previous-choice/outcome history, and
subject-by-environment replication rows. These are descriptive summaries of the
trial sequence and are not treated as model-fitted cognitive history weights.
The fitted model layer separately estimates compact logistic coefficients for
current right/left choice as a function of current signed contrast, previous
choice, previous stimulus side, previous outcome, and previous-choice-by-outcome
interaction within each environment.

Neutral-session adaptation rows are computed from subject-level session order.
Each Neutral session is annotated with the most recent preceding non-Neutral
sequence environment for that subject, if any, then aggregated by Repeating vs
Alternating exposure and neutral-day index. This is an operational carryover
summary, not an inferred latent adaptation state.

## Local Regeneration

```bash
uv run behavtaskatlas fritsche-download
uv run behavtaskatlas fritsche-code-download
uv run behavtaskatlas fritsche-harmonize
uv run behavtaskatlas fritsche-analyze
uv run behavtaskatlas fritsche-code-manifest
uv run behavtaskatlas fritsche-report
uv run behavtaskatlas visual-contrast-family-summary
uv run behavtaskatlas site-index
```

Generated artifacts are written under:

```text
derived/fritsche_temporal_regularities/fritsche-temporal-regularities/
```

Pass repeated `--experiment` flags to `fritsche-harmonize` to restrict the
behavior import to a subset of `exp1_transitional_regularities`,
`exp2_adaptation_test`, and `exp3_photometry_behavior`.

The code manifest inventories Figshare `code.zip`, hashes source scripts, and
records which scripts are reused as behavioral reference material versus
deferred for GLM-HMM, POMDP/RL, IBL-comparison, and photometry work. The same
command emits `artifact_provenance.csv`, with one row per generated atlas
artifact linking outputs to source data files, source fields, source scripts,
and behavior-first scope decisions.
