# MVP Plan: behavtaskatlas

## Aim

Build a public, citable MVP for `behavtaskatlas` that classifies and compares sensory-guided decision-making tasks across species, links them to open data and implementations where available, and provides enough structure for quantitative comparison.

## MVP Definition

The MVP is successful when it contains:

- 30-50 curated task entries focused on sensory decision-making.
- A versioned task schema covering stimulus, evidence, choices, timing, feedback, species, apparatus, training, and provenance.
- At least 10 linked open datasets with harmonized trial-level metadata.
- Baseline psychometric and chronometric summaries for at least 5 datasets.
- A static browsable catalog plus machine-readable JSON/YAML exports.
- Contribution guidelines that make it easy for labs to add a task or dataset.

## Scope

Initial task families:

- Visual 2AFC contrast and orientation discrimination.
- Random-dot motion and motion coherence discrimination.
- Auditory click-rate, tone-frequency, and sound-localization tasks.
- Vibrotactile frequency or flutter discrimination.
- Go/no-go and detection variants.
- Evidence-accumulation tasks with dynamic stimuli.
- Confidence or post-decision wagering variants where they directly extend sensory decisions.
- IBL-style standardized visual decision tasks.

Initial species:

- Mouse.
- Rat.
- Non-human primate.
- Human psychophysics.

Out of scope for the first MVP:

- Full cognitive task coverage.
- Complete neural data mirroring.
- Exhaustive literature coverage.
- Claims that a task measures a latent construct without explicit provenance.

## Workstreams

### 1. Schema and Ontology

Define the canonical task record:

- Identity: task name, aliases, task family, references, maintainers.
- Operational structure: modality, stimulus variable, evidence schedule, choice geometry, response modality, reward or feedback rule.
- Trial timing: fixation, stimulus, delay, response window, feedback, inter-trial interval.
- Context: blocks, priors, volatility, training stages, apparatus, software implementation.
- Population: species, strain or subject type, age range, sex reporting, laboratory context.
- Data availability: raw data links, trial table links, license, format, archive, accession identifiers.
- Analysis availability: psychometric fits, chronometric fits, model fits, notebooks, reproducibility status.
- Interpretive claims: cognitive labels, confidence in label, source, caveats.

Deliverable: `schemas/task.schema.json` plus example records.

### 2. Seed Corpus

Create a first curated task list from canonical studies, standardized projects, and open datasets.

Deliverable: 30-50 task records in `tasks/`, each with references, provenance, and classification fields.

### 3. Data Harmonization

Design a minimal trial table format:

- `subject_id`, `session_id`, `trial_index`.
- `stimulus_modality`, `stimulus_value`, `evidence_strength`, `stimulus_duration`.
- `choice`, `correct`, `response_time`, `feedback`, `reward`.
- `block_id`, `prior_context`, `training_stage`.
- Dataset-specific fields preserved under a namespaced extension.

Deliverable: `schemas/trial_table.schema.json`, example converted datasets, and validation scripts.

### 4. Analysis Baselines

Implement reproducible notebooks or scripts for:

- Psychometric curves.
- Chronometric curves.
- Bias, lapse, threshold, and sensitivity estimates.
- Simple history effects.
- Optional first-pass drift-diffusion or GLM fits for selected datasets.

Deliverable: reproducible analysis outputs for at least 5 datasets.

### 5. Catalog Interface

Build a small static site or documentation portal:

- Search and filter by modality, species, choice type, evidence structure, and data availability.
- Task pages with schema fields, references, diagrams, linked datasets, and available analyses.
- Comparison pages for task families.
- Downloadable JSON/YAML exports.

Deliverable: browsable public catalog suitable for GitHub Pages or similar hosting.

### 5a. Visual UI/UX Roadmap

The next interface layer should make atlas structure visible before asking
users to read dense cards or tables. Visuals should act as wayfinding and
provenance cues, while record pages remain the source of detailed text,
definitions, and citations.

Guiding principles:

- Prefer compact visual summaries over prose-only browse cards.
- Preserve the distinction between operational task variables, source quality,
  model results, and cognitive interpretation.
- Make depth visible within a task family: variation, replication, source
  coverage, and model ambiguity should be scannable.
- Keep every visual tied back to machine-readable records and provenance links.

#### Phase 1: Visual Contrast Family Visual Page

Highest priority because visual contrast 2AFC is currently the deepest family
and should demonstrate the atlas value proposition.

Deliverables:

- A visual-contrast family landing page or section that shows notable papers,
  protocols, species, source-data levels, findings, slices, and model coverage
  in one scannable view.
- A compact coverage matrix with papers or protocols as rows and columns for
  species, curve types, source level, findings, slices, and model fits.
- A paper timeline showing how the family coverage has grown across classic,
  standardized, and recent datasets.
- Links from every visual mark into the paper, finding, slice, or model record.

Success criterion: a user can answer "where is visual contrast deep, where is
it shallow, and which records should I inspect next?" without reading every
paper card.

#### Phase 2: Small-Multiple Curve Galleries

Add visual galleries for dense task-family comparisons, starting with visual
contrast psychometric and chronometric curves.

Status: first pass implemented on `/stories/visual-contrast` with
paper/protocol grouping, pooled/all trace modes, source filtering, source
badges, linked finding traces, and optional model-fit overlays.

Deliverables:

- Small-multiple psychometric galleries by paper, protocol, condition, and
  subject/pooled level.
- Optional chronometric galleries where RT summaries exist.
- Controls for pooled versus subject-level traces, source-balanced summaries,
  and model-fit overlays.
- Visual indicators for source-data level and whether each curve is
  directly observed, extracted from figure data, or derived from a slice.

Success criterion: variation and replication across papers become visually
obvious before users open individual findings.

#### Phase 3: Atlas Overview Dashboard

Create a high-level visual overview for the full atlas, likely on `/` or
`/catalog`.

Status: first pass implemented on `/` with an automatically generated
`AtlasOverview` component. It shows headline counters, a task-family coverage
matrix, source-depth strips, report/finding/model heat cells, dense-family
bars, source-backed gaps, and links into filtered browse views.

Deliverables:

- Task-family by evidence/status heatmap covering species, modality, source
  depth, reports, findings, and model fits.
- Headline visual counters for task families, protocols, datasets, papers,
  findings, slices, and model fits.
- Quick links from sparse or dense cells into filtered `/catalog`, `/papers`,
  `/slices`, and `/models` views.

Success criterion: users can understand the atlas shape, not just its record
count.

#### Phase 4: Paper Coverage Strips

Make `/papers` more visual by adding compact per-paper coverage strips.

Status: first pass implemented on `/papers` with per-paper strips for
bibliography/protocol/source/slice/finding/model coverage, finding/model/slice
mini-bars, curve/source glyphs, and model-fit counts derived from committed
model records.

Deliverables:

- Glyphs or mini-bars for findings, species, source level, curve types, model
  fits, linked slices, and source-access status.
- A visual distinction between paper-level bibliography coverage,
  finding-backed papers, and analysis-linked papers.
- Hover or title text for exact labels while keeping card text compact.

Success criterion: users can scan the paper index for high-value, data-rich,
  or currently blocked papers.

#### Phase 5: Model-Selection Glyphs

Make `/models` less text-heavy and better at conveying ambiguity.

Status: first pass implemented on `/models` with per-answer glyph strips for
winner family, AIC separation, candidate breadth, confidence, source quality,
caveats, and mixed-scope markers, plus family verdict bars for winner-class,
close-call, caveat, and mixed-scope distributions.

Deliverables:

- Compact model-selection glyphs for winner family, AIC separation, number of
  candidates, confidence label, caveats, and source quality.
- Family verdict visuals that summarize which model classes win across a task
  family and where close calls cluster.
- Caveat and mixed-scope markers that are visible without reading the row body.

Success criterion: model confidence and ambiguity become visually scannable
before users open detailed tables.

#### Phase 6: Coverage Gap Matrix

Turn the roadmap and curation queue into a visual triage board.

Deliverables:

- Rows for papers, findings, slices, or model-roadmap targets.
- Columns for raw data, trial table, figure source data, extracted findings,
  model fits, reports, DOI/source request, and current blocker.
- Filterable views for "ready to implement", "blocked external data", and
  "needs extraction".

Success criterion: next curation or implementation work is visible as a
structured set of gaps rather than buried in prose or CSV rows.

Status: first pass implemented on `/atlas-health` with a generated gap matrix
that combines data requests, model-roadmap near misses, and curation queue
items into filterable ready/blocked/extraction views with raw-data,
trial-table, figure-source, finding, model-fit, report, request, and blocker
columns.

### 6. Governance and Contribution

Create a contribution process that supports scientific credit:

- Task submission template.
- Dataset submission template.
- Citation and contributor metadata.
- Lightweight review checklist.
- Versioning and changelog.

Deliverable: contribution guide, review checklist, and issue templates.

## Suggested Repository Structure

```text
.
├── AGENTS.md
├── INSIGHTS.md
├── MVP_PLAN.md
├── schemas/
├── tasks/
├── datasets/
├── analyses/
├── site/
└── docs/
```

## First Four Milestones

1. **Foundation**: create schemas, repository structure, contribution templates, and 3 exemplar task records.
2. **Seed catalog**: curate 30-50 task records with provenance and consistent taxonomy.
3. **Data proof**: harmonize 3-5 open datasets and run baseline psychometric/chronometric analyses.
4. **Public MVP**: publish browsable catalog, exports, documentation, and contribution workflow.

## Immediate Next Actions

1. Create initial schema drafts for task records and trial tables.
2. Select 10 anchor tasks that define the taxonomy boundaries.
3. Identify open datasets for the first data proof, prioritizing IBL and other well-documented archives.
4. Decide whether the catalog should start as a static documentation site, a Python package plus docs, or both.
