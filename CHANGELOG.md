# Changelog

## Unreleased

### Site UI/UX

- Added visual atlas overview counters and task-family coverage matrix to the
  home page.
- Added a visual-contrast family map with paper timeline, coverage matrix,
  curve scan, small-multiple galleries, model-confidence summaries, and
  protocol footprints.
- Added compact paper coverage strips on `/papers`, model-selection glyphs and
  family verdict bars on `/models`, and a generated coverage gap matrix on
  `/atlas-health`.
- Hardened the home overview mobile layout so the wide matrix remains scoped to
  its own horizontal scroll region.

## v0.2.0 — 2026-04-30

Depth release focused on visual contrast coverage, paper visibility, and
model-comparable findings.

### Atlas content

- 7 task families, 18 protocols, 16 datasets.
- 17 vertical slices, with 16 reports currently available and Odoemene kept
  as an explicit follow-up slice.
- 18 curated papers, 91 findings, and 13 finding-backed papers.
- Visual contrast depth expansion: Fritsche temporal regularities, Steinmetz
  distributed coding, Zatka-Haas causal inactivation, and IBL 2025 Brainwide
  Map/prior-map findings are now first-class paper-linked records.
- Five remaining zero-finding papers are visible on `/papers` as
  source-access/request tasks rather than hidden bibliography gaps.

### Models and tooling

- 8 model families, 15 variants, and 222 committed model fits.
- Added logistic-4param and SDT-2AFC fits for all newly promoted
  visual-contrast psychometric findings; the generated model roadmap now has
  `no_fit=0`.
- Paper pages, `/papers`, and headline counts now use the generated paper index,
  so paper coverage updates in one site-index workflow.
- Added a multi-session IBL Brainwide aggregate workflow and explicit finding
  extraction options for aggregate summaries.

### Release health

- Local and GitHub CI run the same release gate: validation, tests,
  finding audit, model audit, site-index, Astro check, and Astro build.
- Current non-blocking release warnings are documented follow-ups: Odoemene
  missing slice artifacts, normal-priority curation queue items, and stale
  ignored per-slice provenance files.

## v0.1.0 — 2026-04-28

First tagged release. behavtaskatlas reaches a substantive
state: curated YAML records, harmonized open-data slices,
cross-paper findings, computational model layer with audit,
and a static Astro site with interactive in-browser fitting.

### Atlas content

- 4 task families, 10 protocols, 8 datasets.
- 9 vertical slices (5 species: human, macaque, mouse, rat,
  + go/no-go change-detection on mouse).
- 8 papers, 77 findings (psychometric, chronometric,
  accuracy-by-strength, hit-rate-by-condition).
- 6 curated cross-paper comparisons.
- 4 model families (logistic, signal-detection,
  drift-diffusion, click-rate-accumulator), 6 variants,
  142 model fits.

### Tooling

- `behavtaskatlas validate / site-index / release-check /
  audit-findings / audit-models / fit-model / fit-stale-models /
  extract-finding / extract-finding --by-subject /
  --by-subject-condition` etc.
- 4-way audit: pooled-vs-by-subject reproducibility,
  model-fit-vs-recorded-predictions consistency, schema
  cross-references, release-readiness.
- 2 CI gates: pytest + ruff + behavtaskatlas validate +
  audit-findings + audit-models + Astro typecheck + Astro build.

### Site

- 16 routes including /findings (interactive overlay with
  Pyodide fits + bootstrap CI), /compare (curated comparisons
  with model-fit AIC tables + parameter strip plots),
  /models (family / variant / fittability map), /models/ddm
  (cross-paper DDM scatter), /audit (reconciliation status),
  /search (cross-record), /papers/[id] (per-paper findings
  + fits), /slices/[id], /protocols/[id], /datasets/[id].
- BibTeX + RIS download (atlas-wide and per-paper) via
  data-URL links.
- Live deploy at <https://behavtaskatlas.vercel.app/>.

### Citation

This release is deposited on Zenodo and gets a versioned DOI.
See `.zenodo.json` and `CITATION.cff`. The README badge will
be populated after the first deposit lands.
