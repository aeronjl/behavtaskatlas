# Contributing to behavtaskatlas

Thanks for your interest. behavtaskatlas is a file-first atlas of
sensory-guided decision-making tasks: half curated YAML records, half Python
tooling that validates the records, harmonizes open datasets, and ships a
static site at <https://behavtaskatlas.vercel.app/>.

This guide covers the most common contributions. For project direction and
design rationale, see [AGENTS.md](AGENTS.md), [MVP_PLAN.md](MVP_PLAN.md), and
the dated entries in [INSIGHTS.md](INSIGHTS.md).

## Ground rules

- Operational task variables come first; cognitive interpretations are sourced
  `InterpretationClaim`s with confidence and caveats.
- Don't broaden MVP scope beyond sensory-guided decision-making without first
  opening an issue.
- Provenance is an artifact, not an afterthought. New analyses must produce
  a JSON provenance payload alongside their outputs.
- Generated files under `derived/` and raw data under `data/raw/` are
  gitignored. Don't commit them.

## Development setup

`behavtaskatlas` uses [`uv`](https://docs.astral.sh/uv/) (Python ≥ 3.11) for
the Python side and [`bun`](https://bun.sh) for the Astro web app under
`web/`.

```bash
uv sync                       # base deps
uv sync --extra ibl           # ONE-api for IBL/mouse-unbiased slices
uv sync --extra clicks        # scipy for clicks slices
uv sync --extra rdm           # scipy for human RDM slice
uv sync --extra visual        # scipy for Walsh human visual slice

cd web && bun install         # frontend deps
```

The canonical full check is:

```bash
bash scripts/ci.sh
```

This runs lint + validate + pytest + site-index + Astro typecheck + Astro
build. GitHub Actions runs the same script and gates merges to `main`.

For finer-grained iteration:

```bash
uv run ruff check src tests           # Python lint (line length 100)
uv run pytest tests/test_X.py::test_Y # one test
uv run behavtaskatlas validate        # YAML schema + cross-ref + vocab
uv run behavtaskatlas site-index      # rebuild derived/ JSON payloads
cd web && bun run check               # Astro typecheck
cd web && bun run build               # Astro build
cd web && bun run dev                 # dev server with hot reload
```

## Adding a new paper or finding

1. Create the YAML record under `papers/` or `findings/`. Follow the schema
   in `src/behavtaskatlas/models.py` (`Paper`, `Finding`, `ResultCurve`,
   `StratificationKey`).
2. If the finding is extracted from a slice's harmonized trials, prefer
   `behavtaskatlas extract-finding` (per slice) and check the result into
   `findings/`.
3. Update the paper's `finding_ids` so the cross-references stay reciprocal.
4. Run `uv run behavtaskatlas validate` to confirm cross-references and
   vocabulary membership.
5. Run `uv run behavtaskatlas site-index` so the new entry appears in
   `derived/findings.json`, `derived/papers.json`, `derived/search.json`,
   and the citation files under `derived/citations/`.

## Adding a new vertical slice

A vertical slice binds one protocol + one dataset to local reproducible
artifacts. The full pattern:

1. Add or extend the YAML records (task family if new, protocol, dataset,
   slice manifest under `vertical_slices/<name>/slice.yaml`).
2. Extend `vocabularies/core.yaml` *only* if a new term is genuinely needed
   — check whether an existing term covers the case first.
3. Add a per-family adapter module under `src/behavtaskatlas/`, or extend
   an existing one. Each adapter exports `download_*`, `load_*`,
   `harmonize_*`, `analyze_*`, and a `*_provenance_payload` helper.
4. Wire CLI subcommands in `src/behavtaskatlas/cli.py` so the slice has the
   `download → harmonize → analyze → report` pipeline (see neighbouring
   slices for the pattern).
5. Add tests under `tests/test_<slice>.py`.
6. Run `bash scripts/ci.sh` and `uv run behavtaskatlas release-check`
   locally before opening a PR.

Aggregate slices (e.g. `clicks-aggregate`) should produce their own
aggregate provenance — see the 2026-04-27 entry in `INSIGHTS.md` for the
rationale.

## Pull requests

- Open an issue first for non-trivial scope changes (new task family,
  new record type, new vocabulary term, large refactor).
- Keep diffs focused. One logical change per PR.
- Run `bash scripts/ci.sh` locally — the same script gates CI.
- Record meaningful design decisions, surprising findings, or unresolved
  concerns as a new top-of-file dated entry in `INSIGHTS.md`. Don't open a
  parallel scratch log.
- Link to the relevant section of `MVP_PLAN.md` if the PR moves the MVP
  forward.

The PR template at `.github/pull_request_template.md` will prompt you for
the same set of items.

## Releasing slice artifacts

The Astro site fetches slice analysis artifacts from the latest
`slice-artifacts-<date>` GitHub Release at build time. To publish updated
artifacts:

1. Run the full slice pipeline locally for every slice that should be
   refreshed.
2. Run `bash scripts/release-slice-artifacts.sh` (if present) or follow the
   manual workflow under `.github/workflows/slice-artifacts.yml`.
3. The next Vercel deploy will pick up the new release tarball; verify the
   `derived/release_status.json` summary and the slice cards on the live
   site.

## Reporting issues

Open a GitHub issue with:

- A short title scoped to one record type or feature.
- The exact `behavtaskatlas` command run (or page visited) and what was
  expected vs. observed.
- For data issues, reference the offending record id (e.g.
  `dataset.palmer-huk-shadlen-human-rdm-cosmo2017`) and source URL.
