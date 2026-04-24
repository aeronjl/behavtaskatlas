# behavtaskatlas

`behavtaskatlas` is a file-first atlas for sensory-guided decision-making tasks in behavioral neuroscience.

The MVP goal is to make task protocols comparable by linking operational task structure, provenance, open datasets, implementations, and reproducible analysis expectations.

## Current Scope

- Human-authored YAML records for task families, protocols, datasets, and related artifacts.
- Controlled vocabularies for core comparative fields.
- Python validation tooling for schema and cross-reference checks.
- Three seed task families and protocols:
  - IBL visual decision task.
  - Random-dot motion discrimination.
  - Auditory click evidence accumulation.

## Local Workflow

Install and validate with `uv`:

```bash
uv sync
uv run behavtaskatlas validate
```

Run tests:

```bash
uv run pytest
```

Export JSON schemas from the Pydantic models:

```bash
uv run behavtaskatlas export-schemas
```

Generate the first IBL visual decision slice artifacts:

```bash
uv sync --extra ibl
uv run behavtaskatlas ibl-harmonize
uv run behavtaskatlas ibl-analyze
uv run behavtaskatlas ibl-report
```

Generated trial tables, summaries, analysis results, plots, and provenance files are written under `derived/`, which is ignored until data release policy is settled.
The default IBL session loader selects the OpenAlyx default `_ibl_trials.table.pqt` revision and records the selected revision, dataset id, hash, and QC state in provenance.
To override the selected table revision:

```bash
uv run --extra ibl behavtaskatlas ibl-harmonize --revision 2025-03-03
```

Download the Brody Lab clicks archive locally, then run the auditory-clicks slice from
one extracted `.mat` file:

```bash
mkdir -p data/raw/brody_clicks
curl -L -C - --fail --retry 5 --retry-delay 10 \
  -o data/raw/brody_clicks/Brody_Lab_Poisson_Clicks_Task_Dataset_Rats_2009_to_2024_Parsed_.zip \
  https://zenodo.org/api/records/13352119/files/Brody_Lab_Poisson_Clicks_Task_Dataset_Rats_2009_to_2024_Parsed_.zip/content
```

The archive uses ZIP64/Deflate64 compression. On macOS, install `p7zip` and
extract a rat file with `7z`:

```bash
brew install p7zip
7z x -y -odata/raw/brody_clicks/extracted \
  data/raw/brody_clicks/Brody_Lab_Poisson_Clicks_Task_Dataset_Rats_2009_to_2024_Parsed_.zip \
  B075.mat
```

```bash
uv sync --extra clicks
uv run behavtaskatlas clicks-harmonize --mat-file data/raw/brody_clicks/extracted/B075.mat
uv run behavtaskatlas clicks-analyze --session-id B075-parsed
uv run behavtaskatlas clicks-batch --mat-dir data/raw/brody_clicks/extracted --max-files 5
uv run behavtaskatlas clicks-aggregate
uv run behavtaskatlas clicks-report
uv run behavtaskatlas site-index
```

The clicks archive is large and remains ignored under `data/raw/`; derived artifacts
are written under ignored `derived/auditory_clicks/`. The clicks analysis emits
both a baseline psychometric summary and a descriptive click-time evidence kernel.
Batch runs also write `derived/auditory_clicks/batch_summary.csv`. Aggregate runs
read those existing batch outputs and write a per-rat/gamma psychometric bias table,
a cross-rat evidence-kernel summary, a JSON result, and an SVG plot. Report runs
render those aggregate artifacts as a dependency-free static HTML page.

Build the local static report index:

```bash
uv run behavtaskatlas site-index
```

This writes `derived/index.html`, linking available vertical-slice reports and
generated analysis artifacts without committing raw or derived data.

## Repository Layout

```text
.
├── analyses/          # Analysis plans, outputs, and later reproducible scripts
├── datasets/          # Dataset metadata records
├── docs/              # Design notes and contributor-facing documentation
├── implementations/   # Task implementation metadata records
├── protocols/         # Concrete protocol records
├── schemas/           # Generated JSON schemas
├── src/               # Python validation package
├── task_families/     # Abstract task-family records
├── tests/             # Validation tests
├── vertical_slices/   # Deep end-to-end MVP slices
└── vocabularies/      # Controlled vocabulary source files
```
