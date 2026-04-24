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
