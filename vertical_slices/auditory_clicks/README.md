# Auditory Clicks Slice

This is the second vertical slice for `behavtaskatlas`.

## Goal

Stress the atlas beyond scalar visual contrast by mapping a dynamic auditory evidence-accumulation task into the canonical trial model.

## Source Protocol

- Protocol record: `protocol.poisson-clicks-evidence-accumulation`
- Dataset record: `dataset.brody-lab-poisson-clicks-2009-2024`
- Source archive: Brody Lab Poisson Clicks Task Dataset Rats 2009 to 2024 Parsed
- DOI: `10.5281/zenodo.13352119`

## Source Fields

The first adapter targets the parsed MATLAB schema described by the Zenodo record:

- `nL`: number of left evidence clicks.
- `nR`: number of right evidence clicks.
- `sd`: stimulus duration in seconds.
- `gr`: go right, with `0` left and `1` right.
- `hh`: hit history, with `0` incorrect and `1` correct.
- `ga`: gamma value used to generate the stimulus.
- `rg`: reward gamma.
- `bt`: click-time metadata; at minimum `left` and `right` click-time vectors.

## Canonical Mapping

| Canonical field | Source |
| --- | --- |
| `stimulus_value` | `nR - nL` |
| `stimulus_side` | sign of `nR - nL` |
| `evidence_strength` | `abs(nR - nL)` |
| `choice` | `gr`: `0` left, `1` right |
| `correct` | `hh`: `0` incorrect, `1` correct |
| `feedback` | `hh` mapped to error/reward |
| `prior_context` | `ga` formatted as gamma context |
| `task_variables.left_click_count` | `nL` |
| `task_variables.right_click_count` | `nR` |
| `task_variables.left_click_times` | `bt.left` |
| `task_variables.right_click_times` | `bt.right` |

## Current Implementation

- Adapter: `src/behavtaskatlas/clicks.py`
- Tests: `tests/test_clicks.py`
- Dataset metadata: `datasets/brody-lab-poisson-clicks-2009-2024.yaml`

## Local Regeneration Command

Download the archive under ignored local raw-data storage:

```bash
mkdir -p data/raw/brody_clicks
curl -L -C - --fail --retry 5 --retry-delay 10 \
  -o data/raw/brody_clicks/Brody_Lab_Poisson_Clicks_Task_Dataset_Rats_2009_to_2024_Parsed_.zip \
  https://zenodo.org/api/records/13352119/files/Brody_Lab_Poisson_Clicks_Task_Dataset_Rats_2009_to_2024_Parsed_.zip/content
```

The archive uses ZIP64/Deflate64 compression. On macOS, `7z` from `p7zip`
extracts it reliably:

```bash
brew install p7zip
7z x -y -odata/raw/brody_clicks/extracted \
  data/raw/brody_clicks/Brody_Lab_Poisson_Clicks_Task_Dataset_Rats_2009_to_2024_Parsed_.zip \
  B075.mat
```

Then run:

```bash
uv sync --extra clicks
uv run behavtaskatlas clicks-harmonize --mat-file data/raw/brody_clicks/extracted/B075.mat
uv run behavtaskatlas clicks-analyze --session-id B075-parsed
```

Run a local batch over extracted rat files:

```bash
uv run behavtaskatlas clicks-batch --mat-dir data/raw/brody_clicks/extracted --max-files 5
uv run behavtaskatlas clicks-aggregate
uv run behavtaskatlas clicks-report
```

By default this writes ignored local artifacts under:

```text
derived/auditory_clicks/
```

Verified local smoke run:

- Source file: `B075.mat`
- Parsed trials: 11,285
- Summary rows: 181 grouped by gamma context and signed click-count difference
- Psychometric artifacts: `psychometric_summary.csv`, `analysis_result.json`, `psychometric.svg`
- Evidence-kernel artifacts: `evidence_kernel_summary.csv`, `evidence_kernel_result.json`, `evidence_kernel.svg`
- Prior contexts: `gamma=-1`, `gamma=-2`, `gamma=-4`, `gamma=1`, `gamma=2`, `gamma=4`
- Kernel bins: 10 normalized stimulus-time bins; all 11,285 B075 parsed trials included
- Output directory: `derived/auditory_clicks/B075-parsed/`

Verified local batch run:

- Source files: `A080.mat`, `B075.mat`, `B127.mat`, `T014.mat`, `T074.mat`
- Status: 5 ok, 0 failed
- Parsed trials: 61,222 total
- Harmonization/psychometric summary rows: 1,551 total
- Evidence-kernel rows: 10 per rat
- Batch summary: `derived/auditory_clicks/batch_summary.csv`

Verified local aggregate run:

- Batch rows: 5 ok, 0 failed, 0 aggregate artifact errors
- Parsed trials: 61,222 total
- Per-rat/gamma psychometric bias rows: 44
- Aggregate evidence-kernel rows: 10 normalized stimulus-time bins
- Task types: `location`
- Gamma contexts: 18 distinct labels across the five rats
- Aggregate files: `aggregate_psychometric_bias.csv`, `aggregate_kernel_summary.csv`,
  `aggregate_result.json`, `aggregate_kernel.svg`
- Mean choice-triggered evidence rises from 0.92 in the first normalized time bin
  to about 1.4 clicks through later bins, confirming that the batch aggregate is
  reading the per-rat click-time kernels rather than only scalar click counts.

Verified local report run:

- Static report: `derived/auditory_clicks/report.html`
- Source inputs: `aggregate_result.json` and `aggregate_kernel.svg`
- Contents: top-level aggregate metrics, coverage/provenance, inline evidence-kernel
  SVG, per-rat table, per-rat/gamma psychometric table, kernel summary table, links
  to generated aggregate CSV/JSON/SVG files, and caveats.

## Data Policy

The Zenodo archive is 8.1 GB. It is acceptable to download locally for MVP development, but raw archives and extracted `.mat` files stay under ignored `data/raw/`. Real ingestion should operate on local `.mat` files from the archive or on a small extracted fixture if release policy allows.

## Next Steps

1. Upgrade the descriptive evidence kernel to a multivariate click-time weighting model.
2. Decide whether to support MATLAB v7.3/HDF5 files if future archive releases require it.
3. Add a matching static report for the IBL visual-decision slice so the site index has two complete report pages.
