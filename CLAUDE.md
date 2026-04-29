# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`behavtaskatlas` is a file-first atlas of sensory-guided decision-making tasks. The repository is half curated YAML records (task families, protocols, datasets, implementations, vertical slices) and half Python tooling (`src/behavtaskatlas/`) that validates those records, harmonizes open datasets into a canonical trial table, runs baseline analyses, and generates a static site plus a release-readiness check. Raw data and generated artifacts under `data/raw/` and `derived/` are gitignored.

See `AGENTS.md` and `MVP_PLAN.md` for project-direction guardrails. **Important:** every meaningful research finding, design decision, or unresolved concern must be recorded as a new top-of-file dated entry in `INSIGHTS.md` — that file is the single progress log; do not create parallel scratch logs.

## Common Commands

Python tooling uses `uv` (Python ≥ 3.11); the web frontend uses `bun`. Both must be on PATH for `scripts/ci.sh`.

```bash
uv sync                              # base dependencies
uv sync --extra ibl                  # ONE-api for IBL/mouse-unbiased slices
uv sync --extra clicks               # scipy for clicks slices
uv sync --extra rdm                  # scipy for human RDM slice
uv sync --extra visual               # scipy for Walsh human visual slice
```

Validate, test, lint, schema export:

```bash
bash scripts/ci.sh                   # canonical full check (lint + validate + pytest +
                                     # audit-findings + audit-models + site-index +
                                     # Astro typecheck + Astro build). GitHub Actions
                                     # runs this exact script.
uv run behavtaskatlas validate       # YAML schema + cross-ref + vocabulary checks
uv run behavtaskatlas audit-findings # pooled vs by-subject reconciliation
uv run behavtaskatlas audit-models   # forward-eval drift detection on ModelFits
uv run pytest                        # full test suite
uv run pytest tests/test_clicks.py::test_name   # single test
uv run ruff check src tests          # lint (config in pyproject.toml; line-length 100)
uv run behavtaskatlas export-schemas # regenerate schemas/*.schema.json from Pydantic models
```

Web frontend (Astro, in `web/`):

```bash
cd web && bun install                # install JS deps
cd web && bun run check              # Astro/TypeScript typecheck
cd web && bun run build              # static build; consumes JSON written by site-index
```

Build the static site and release check (operates on whatever slices are present locally under `derived/`):

```bash
uv run behavtaskatlas site-index
uv run behavtaskatlas release-check
```

Each vertical slice has its own pipeline of `<slice>-download → <slice>-harmonize → <slice>-analyze → <slice>-report` subcommands (see `README.md` for per-slice invocations including `ibl-*`, `mouse-unbiased-*`, `clicks-*`, `human-clicks-*`, `rdm-*`, `human-rdm-*`, `macaque-rdm-confidence-*`, `human-visual-*`). Slice subcommands write under `derived/<slice>/` and are wired into the site-index manifest.

## Architecture

### Object model (the curation layer)

Curation records live as YAML under top-level directories that mirror the JSON schemas in `schemas/`. Two layers exist: the original five-level task/data layer, and a meta-analysis/model layer layered on top.

Task/data layer (`docs/object_model.md`):

- **Task family** (`task_families/*.yaml`) — reusable operational idea.
- **Protocol** (`protocols/*.yaml`) — concrete task variant; can be `template` or `concrete`. Concrete multi-species protocols must declare `template_protocol_id`.
- **Dataset** (`datasets/*.yaml`) — link to public/private data; carries `source_data_level` ∈ {`raw-trial`, `processed-trial`, `processed-session`, `figure-source-data`, `aggregate-only`}.
- **Implementation** (`implementations/*.yaml`) — task-control code reference.
- **Vertical slice** (`vertical_slices/<name>/slice.yaml`) — binds one protocol + one dataset to local reproducible artifacts (harmonized trials, analysis outputs, plots, report HTML, provenance). Each slice repeats `source_data_level` so the atlas can show report availability and source strength side by side.

Meta-analysis / model layer:

- **Paper** (`papers/*.yaml`) — bibliographic anchor for findings extracted from the literature.
- **Finding** (`findings/*.yaml`) — one curve/group of behavioral data (psychometric, chronometric, accuracy, hit-rate, etc.) attached to a paper and optionally a slice. Carries the x/y points used to refit and audit.
- **Model family / variant / fit** (`model_families/`, `model_variants/`, `model_fits/`) — models are declared as families with concrete variants (e.g. `signal-detection` → `sdt-2afc`); `ModelFit` records bind a variant to a finding with fitted parameters and (optionally) cached predictions. The forward-eval audit re-runs predictions to detect drift between fit-time and current code.
- **Comparison** (`comparisons/*.yaml`) — cross-finding summary view (e.g. drift-across-species).
- **Data request** (`data_requests/*.yaml`) — tracked outreach for unreleased data.

`vocabularies/core.yaml` is the single source of truth for controlled-vocab fields (species, modalities, evidence types, choice types, response modalities, source data levels, curation statuses, feedback types). `validation.py` rejects any value not present there.

### Python package (`src/behavtaskatlas/`)

- `models.py` — Pydantic v2 `StrictModel` (extra=forbid) classes for all record types and the `CanonicalTrial` row schema. `SCHEMA_MODELS` drives JSON-schema export.
- `validation.py` — loads YAML, dispatches to the right model via `model_from_record`, then runs cross-reference checks (family↔protocol↔dataset↔slice consistency, dataset_id reciprocity, template hierarchy, vocabulary membership). Also validates the model layer (paper↔finding↔fit↔variant↔family).
- `ibl.py`, `clicks.py`, `rdm.py`, `human_visual.py`, `allen.py` — per-family adapters. Each exports `download_*`, `load_*`, `harmonize_*` (→ canonical trial CSV), `analyze_*`, `*_provenance_payload`, and writers for CSV/SVG/HTML report. Adapters share the canonical trial schema; slice-specific extensions go in a namespaced `task_variables` field rather than new top-level columns.
- `findings.py` — extracts `Finding` records from slice psychometric summaries and walks all `papers/` + `findings/` YAML into the denormalized `findings_index.json` consumed by the web build. Curve-type extractors are added narrowly as new finding shapes are needed.
- `model_layer.py` + `model_fits/` package (`accuracy`, `bernoulli`, `chronometric`, `clicks`, `ddm`, `logistic`, `sdt`) — forward-evaluation dispatchers per `ModelFamily`/`ModelVariant`. Variants without a registered forward function get `forward_unimplemented` status from the audit rather than silently passing.
- `audit.py` — pooled-vs-by-subject reconciliation across findings; surfaces inconsistencies as audit failures.
- `search.py` — builds the search index JSON consumed by `web/src/pages/search.astro`.
- `citations.py`, `link_integrity.py`, `data_requests.py` — citation harvesting, external-link checks, and data-request tracking for the curation queue.
- `static_site.py` — builds the static index, catalog, relationship graph, curation queue, findings/models indexes, and per-record detail JSON from the YAML records plus any locally generated slice manifests under `derived/`. Output JSON under `derived/` (or `web/public/`) is what the Astro build consumes.
- `release.py` — produces `derived/release_status.{json,html}`. Blocks release on validation errors, stale generated payloads (must match a clean commit), missing slice reports/analyses, non-empty curation queue, and accidental `data/raw` links in publishable payloads. Treats per-slice provenance staleness as a warning.
- `cli.py` — single argparse entry point (`behavtaskatlas` script). Heavy and procedural: each slice has its own `subparsers.add_parser` block plus a matching `if args.command == ...` branch in `main()`.

### Web frontend (`web/`)

Astro static site (deployed to Vercel). Pages under `web/src/pages/` — catalog, datasets, papers, protocols, slices, findings, models, audit, curation queue, search, comparisons — load JSON written by `behavtaskatlas site-index` via helpers in `web/src/lib/`. The site is purely a reader of the Python pipeline's output; do not put curation logic in the frontend. Some pages also expose CSV endpoints (`*.csv.ts`) derived from the same JSON.

### Provenance discipline

Provenance is an artifact, not an afterthought. Each slice writes a JSON provenance payload alongside its outputs recording dataset id/revision/hash, adapter version, parameters, commit, and dirty state. Aggregate slices (e.g. `clicks-aggregate`) produce their own aggregate provenance rather than borrowing one input session's provenance — see the 2026-04-27 entry in `INSIGHTS.md`. The release check verifies this end-to-end.

### Generated vs. committed

- **Committed:** YAML records, vocabularies, schemas (`schemas/*.schema.json` are generated from models but checked in), Python source, tests, slice READMEs and `slice.yaml` manifests.
- **Ignored:** `data/raw/**`, `derived/**`, `.venv`, caches. The static site and release check both assume `derived/` is local-only and must not leak `data/raw/` paths into publishable JSON.

## Conventions

- Operational task variables come first; cognitive interpretations only as sourced `InterpretationClaim`s with confidence and caveats.
- Don't broaden MVP scope beyond sensory-guided decision-making without explicit user direction.
- When adding a new slice: add the YAML records (family if new, protocol, dataset, slice), extend `vocabularies/core.yaml` if a new term is genuinely needed, add a per-family module or extend an existing one, register CLI subcommands, write tests under `tests/test_<slice>.py`, and run `validate` + `site-index` + `release-check` locally before committing.
