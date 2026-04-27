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
- Nine current protocol records: one abstract template and eight report-backed
  concrete protocols.

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
a cross-rat evidence-kernel summary, a JSON result, an aggregate provenance JSON,
and an SVG plot. Report runs render those aggregate artifacts as a
dependency-free static HTML page.

Download and run the Mendeley Data human Poisson clicks DBS OFF/ON slice:

```bash
uv run --extra clicks behavtaskatlas human-clicks-download
uv run --extra clicks behavtaskatlas human-clicks-harmonize
uv run --extra clicks behavtaskatlas human-clicks-analyze
uv run --extra clicks behavtaskatlas human-clicks-report
uv run behavtaskatlas site-index
```

The human clicks slice writes ignored local artifacts under
`derived/human_auditory_clicks/london-dbs-poisson-clicks-mendeley/`. It emits
canonical trials, DBS-context psychometrics, a response-window click-time
evidence kernel, dependency-free SVG plots, and a static report. The raw
Mendeley MATLAB file stays under ignored `data/raw/human_clicks_mendeley/`.

Download and run the Roitman-Shadlen random-dot motion slice from the pinned
processed PyDDM CSV:

```bash
uv run behavtaskatlas rdm-download
uv run behavtaskatlas rdm-harmonize
uv run behavtaskatlas rdm-analyze
uv run behavtaskatlas rdm-report
uv run behavtaskatlas site-index
```

The RDM slice writes ignored local artifacts under
`derived/random_dot_motion/roitman-shadlen-pyddm/`. It emits canonical trials,
psychometric and chronometric summaries, descriptive fit results, dependency-free
SVG plots, and a static report. The raw processed CSV stays under ignored
`data/raw/random_dot_motion/`.

Download and run the Palmer-Huk-Shadlen human random-dot motion slice from the
pinned CoSMo2017 MATLAB files:

```bash
uv run --extra rdm behavtaskatlas human-rdm-download
uv run --extra rdm behavtaskatlas human-rdm-harmonize
uv run behavtaskatlas human-rdm-analyze
uv run behavtaskatlas human-rdm-report
uv run behavtaskatlas site-index
```

The human RDM slice writes ignored local artifacts under
`derived/human_random_dot_motion/palmer-huk-shadlen-cosmo2017/`. It emits
canonical trials, psychometric and chronometric summaries, descriptive fit
results, dependency-free SVG plots, and a static report. The raw MATLAB files
stay under ignored `data/raw/human_random_dot_motion/`.

Download and run the macaque RDM confidence/wagering slice from the Khalvati,
Kiani, and Rao Nature Communications source-data ZIP:

```bash
uv run behavtaskatlas macaque-rdm-confidence-download
uv run behavtaskatlas macaque-rdm-confidence-harmonize
uv run behavtaskatlas macaque-rdm-confidence-analyze
uv run behavtaskatlas macaque-rdm-confidence-report
uv run behavtaskatlas site-index
```

The macaque confidence slice writes ignored local artifacts under
`derived/macaque_rdm_confidence/khalvati-kiani-rao-natcomm2021-source-data/`.
It emits canonical source-data rows, accuracy and sure-target choice summaries,
dependency-free SVG plots, and a static report. The raw source-data ZIP stays
under ignored `data/raw/macaque_rdm_confidence_khalvati/`.

Generate the mouse unbiased visual contrast training slice from the pinned
OpenAlyx trainingChoiceWorld session:

```bash
uv run --extra ibl behavtaskatlas mouse-unbiased-harmonize \
  --cache-dir data/raw/openalyx-cache
uv run behavtaskatlas mouse-unbiased-analyze
uv run behavtaskatlas mouse-unbiased-report
uv run behavtaskatlas site-index
```

This writes ignored local artifacts under
`derived/mouse_visual_contrast_unbiased/6a6442d1-dd7d-4717-b7b1-5874aefbd6fc/`.
It reuses the IBL canonical trial adapter while stamping trials with the
mouse-unbiased protocol id.

Download and run the Walsh et al. human visual contrast prior-cue slice from
OSF:

```bash
uv sync --extra visual
uv run --extra visual behavtaskatlas human-visual-download
uv run --extra visual behavtaskatlas human-visual-harmonize
uv run behavtaskatlas human-visual-analyze
uv run behavtaskatlas human-visual-report
uv run behavtaskatlas site-index
```

The human visual contrast slice writes ignored local artifacts under
`derived/human_visual_contrast/walsh-prior-cue-human-contrast-osf/`. It emits
canonical trials, cue-split psychometric summaries, a descriptive fit result,
a dependency-free SVG plot, and a static report. The raw OSF downloads stay
under ignored `data/raw/human_visual_contrast_walsh/`.

Run the Allen Brain Observatory Visual Behavior change-detection slice from a
local Visual Behavior NWB file:

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

The Allen slice writes ignored local artifacts under
`derived/allen_visual_behavior/`. It emits canonical trials with go/withhold
choice values, an outcome-count summary, a per-image-pair hit-rate table, a
hit lick-latency SVG histogram, and a static report. The adapter reads the
NWB trials table with `h5py` rather than `allensdk`, because allensdk pins
`scipy<1.11` and conflicts with the project's other scipy-dependent extras.

Build the local static report index:

```bash
uv run behavtaskatlas site-index
uv run behavtaskatlas release-check
```

This writes `derived/index.html`, `derived/manifest.json`, `derived/catalog.html`,
`derived/catalog.json`, `derived/graph.html`, `derived/graph.json`,
`derived/curation_queue.html`, `derived/curation_queue.json`, one
`derived/protocol-*.html` detail page per protocol, and one
`derived/dataset-*.html` detail page per dataset from the committed YAML records.
The report index links available vertical-slice reports, shows a cross-slice
comparison table, shows an MVP health dashboard, and links generated analysis
artifacts without committing raw or derived data. The health dashboard separates
raw-trial, processed-trial, processed-session, figure-source-data, and
aggregate-only slices so source strength is visible next to report availability.
The catalog lists task families, protocols, datasets, and linked slices,
including records whose reports have not yet been generated locally. The
JSON files carry the same data for downstream tooling. The catalog HTML also
includes dependency-free protocol search and filters for species, modality,
evidence type, and report status, with protocol and dataset rows linking to
their generated detail pages. The relationship graph exposes task-family,
protocol, dataset, and vertical-slice nodes plus typed edges as both HTML and
machine-readable JSON. Protocol graph edges also distinguish template protocols
from concrete protocol variants. The graph export carries lightweight QA issues
for orphan records, missing reciprocal links, concrete protocols without
datasets, concrete protocols without slices, and datasets without slices. The
curation queue turns those graph QA issues into contributor-facing action items
grouped by action type and priority.

The release check writes `derived/release_status.json` and
`derived/release_status.html`. It validates the repository records and generated
static JSON, checks that the static payloads match the current clean commit,
confirms that every vertical slice has a report and analysis artifact, requires
an empty curation queue, scans publishable payloads for accidental `data/raw`
links, and reports per-slice provenance staleness as a warning.

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
├── vertical_slices/   # Deep end-to-end MVP slices and slice manifests
└── vocabularies/      # Controlled vocabulary source files
```
