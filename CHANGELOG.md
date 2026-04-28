# Changelog

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
