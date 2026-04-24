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
```

By default this writes ignored local artifacts under:

```text
derived/auditory_clicks/
```

Verified local smoke run:

- Source file: `B075.mat`
- Parsed trials: 11,285
- Summary rows: 181
- Output directory: `derived/auditory_clicks/B075-parsed/`

## Data Policy

The Zenodo archive is 8.1 GB. It is acceptable to download locally for MVP development, but raw archives and extracted `.mat` files stay under ignored `data/raw/`. Real ingestion should operate on local `.mat` files from the archive or on a small extracted fixture if release policy allows.

## Next Steps

1. Decide whether to support MATLAB v7.3/HDF5 files if scipy cannot read the archive files.
2. Generate the first real click-count psychometric summary for one rat.
3. Add an evidence-kernel or click-time weighting analysis after the trial table is verified.
