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
```

Generated trial tables, summaries, and provenance files are written under `derived/`, which is ignored until data release policy is settled.

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
