# Critique of behavtaskatlas — toward a standout scientific UI

This document is a thorough audit of the current Astro+Svelte frontend under
`web/` (every top-level page, design tokens, all `ui/` primitives, the heaviest
interactive components, the encoding bridge, and the layout shell), cross-checked
against the live deploy at https://behavtaskatlas.vercel.app.

It is structured as: existing strengths → five themes that hold the UI back →
per-page critique → accessibility & responsiveness → delight & exploration →
prioritized roadmap.

---

## Where you already are

Before the criticism, the foundation is genuinely good and worth preserving:

- **The design system has matured.** `web/src/styles/global.css` is one of the
  cleaner Tailwind v4 `@theme` setups: a real type ramp (display→eyebrow + two
  mono variants), three explicit container widths, semantic surfaces
  (`surface / raised / sunken / accent / warn / ok / bad`), foreground hierarchy
  (`fg / fg-secondary / fg-muted / fg-subtle`), an encoding palette per axis
  (source level, curve type, model family, node type, coverage status,
  confidence), and a `color-mix` derivation for the `*-soft / *-strong / *-edge`
  chip triplets. Strong vocabulary.
- **`web/src/lib/encoding.ts` bridges CSS variables to chart colors at runtime
  via `getComputedStyle`** so Vega specs and the SVG graph share a single
  palette. The right architecture for a future dark mode and for keeping legend
  chips and curve colors in sync.
- **The `ui/` primitives (`Card`, `Stat`, `StatGrid`, `Section`, `PageHeader`,
  `DataTable`, `StatusPill`, `DetailLayout`, `DetailToc`, `SectionAnchorNav`)**
  are well-shaped, composable, and used consistently in newer pages.
- **The mechanics behind the data are exceptional:** Vega-Lite axes, in-browser
  Pyodide refits with bootstrap CIs, AIC selection with a confidence taxonomy,
  build-time deltas on `/compare`, a force-directed graph, URL-state sync on the
  major filters, ⌘K palette, and a print stylesheet. As a *capability set*,
  this is well beyond most public neuroscience portals.
- **Detail pages with sticky rails + ToC + RecordChip** are exactly the right
  pattern for cross-linked records.

The shortfall is not capability. It is *expression*: too much of the surface
area still presents itself as a tabular dump of well-curated YAML rather than as
a place a scientist would want to spend an afternoon.

---

## The five themes that hold the UI back

### 1) The mental model isn't on the page

The atlas's core idea — Family ⊃ Protocol ⊃ Dataset ⊃ Slice → Finding → Model
fit — is the most distinctive thing about it. It is on `/about` in prose, but
not visible anywhere a working researcher would look first. Every page assumes
the reader already knows the schema.

What's missing is a *single canonical map*: a small, persistent diagram (could
be 5 nodes and 4 edges in an SVG, ~40 lines) anchored either in the nav region
or at the top of the home page, where each node is a count, hover surfaces what
it means, and click filters the catalog. Right now `/graph` does a force layout
of all 90 nodes — useful for exploration, useless for orientation. The home
`AtlasOverview` matrix is the closest thing, but it's a 10-column data table,
not a model.

The label "References" for `/graph` in the secondary nav reads as "bibliography"
to anyone outside the project. Rename.

### 2) The home page tries to be six pages

`pages/index.astro` opens with: `PageHeader` → `AtlasOverview` (matrix + 7 KPI
tiles + deepest families + source-backed gaps) → featured comparison Card with
chart → "Where to start" 4-card grid → "Latest story" card → 2-column "Across
the literature" stats + species table + build-state aside. That's 6 visual
systems competing above the second scroll, none of them dominant.

A landing page that wants to reward exploration needs *one* strong hook. Right
now `AtlasOverview` is doing both "summary KPI" and "interactive coverage
matrix", and the matrix loses that competition because it is the densest object
on the page (10 columns, heat-mapped cells, monospace integers, action chips).
A first-time scientist sees a spreadsheet.

A confident landing would pick one of:

- a *story* — one finding, one chart, one paragraph: "Across 71 psychometric
  findings from 13 papers and 4 species, the median 75% threshold is 0.27
  [signed coherence] but mouse and macaque differ by..." with a live chart;
- a *map* — the Family→Protocol→Dataset→Slice diagram with hot zones the user
  can step through; or
- a *demo* — the Pyodide refit running on first paint with a dataset of the
  user's choosing.

The existing six blocks can live below the fold or move to `/atlas-health`.

### 3) The encoding system is built but only half-wired

The tokens in `global.css` exist for exactly the surfaces that are currently
bypassing them:

- `Nav.astro` still uses
  `border-slate-200 bg-white text-slate-900 / text-slate-700 / text-slate-500` —
  never touches the new tokens.
- `AtlasOverview.astro` hand-rolls heat-map cells with inline
  `rgba(79, 70, 229, ...)` for papers, `rgba(16, 185, 129, ...)` for datasets,
  etc. — none of which are the `encoding-*` variables. The source-level strip
  uses `bg-emerald-500 / bg-sky-500 / bg-amber-500` instead of
  `bg-encoding-source-raw / processed / figure`.
- `atlas-health.astro` mixes `border-slate-200 bg-white text-slate-700` with
  `bg-warn-soft text-warn` in adjacent `<details>` blocks.
- `models.astro` has hand-coded `bg-amber-50 text-amber-800 ring-amber-200`
  action pills (in `AtlasOverview.astro`) and `border-slate-200 bg-white`
  chrome alongside `Card`-tokenized siblings.
- A trailing `<style>` block in `AtlasOverview.astro` re-asserts
  `a.no-underline { text-decoration: none }` even though `global.css` already
  does it.

The visual cost is a UI that *almost* feels coherent — the same color, but with
five subtly different shades of "white", four different shades of
"border-slate-200/300", three different chip styles for source level depending
on which page you're on. A pass that swaps every `slate-` literal for the
`fg-/rule-/surface-/encoding-` tokens (and deletes the orphan `<style>` blocks)
would make the system feel snapped together.

### 4) Density without graduated entry

`/models` is the clearest case. The page is 1044 lines of Astro, eight sections,
three Svelte browsers, two strip plots, a coverage gap quartet, a fittability
table, all the families/variants, and a flat `fits` table. The live fetch
confirmed it: *"requires significant investment to extract insights."*

The same shape applies to `/atlas-health` (gap matrix, audit, curation,
blockers, roadmap, links, request queue), to `/findings` (4 control rows +
filter accordion + chart + flat-table fold-out), and to `/compare` (per-comparison
Card with sub-MiniFindingsChart + DDM strip + model-fit table + parameter-delta
table).

Density is not the enemy — scientists will tolerate density. What's missing is
*graduated entry*: a one-screen executive view at the top, an
overview-of-overview before the dashboards begin. Today every section has equal
visual weight.

A workable pattern for `/models`:

1. **One big sentence**: "91 findings, 222 fits across 15 variants. DDM wins
   decisively on 17, supportedly on 12; SDT wins on 9; logistic wins on 31. 27
   findings still have only one candidate."
2. **One chart**: a strip plot of best-AIC variant by curve type, colored by
   confidence.
3. *Then* the rest, in a `<details>`-style progressive reveal, with each
   subsection labeled by *the question it answers* rather than by the artifact
   name.

Section names like "Per-finding selection" / "Selection matrix" /
"Slice fittability" are *artifacts*, not questions. A scientist arrives with
questions: "Which model wins for RDM in macaques?" "Which slices could fit a
DDM if I added one variable?" "Where are AIC winners contradicting the original
paper?" Rename sections accordingly.

### 5) Provenance, caveats, and uncertainty are present but invisible

The atlas is unusual for caring about reproducibility — `dirty/clean fit` pills,
source-data-level caveats, scope-mixing warnings, audit-drift status, commit
hashes — and that's the most defensible thing about it as an open-science tool.
But this signal is mostly hidden:

- The slice detail page shows `report available / no report` as a `StatusPill`
  and a paragraph, but the dataset hash, adapter version, fit commit, and
  pipeline run timestamp aren't surfaced together. To know "is this the version
  I should cite?" a scientist has to find `provenance` deep in the artifact list.
- Caveat tags on `/models` use `bg-warn-soft text-warn` chips with
  `caveatDefinitions[tag]?.description ?? tag` as a `title` tooltip. Tooltip-only
  descriptions fail keyboard users and most mobile users; they also disappear on
  print.
- The confidence palette (decisive/supported/close/single) is a beautiful
  taxonomy that gets reduced to a 1-line text label in tables. Encode it in a
  small horizontal stack chip — `[██░░] supported (Δ 4.2)` — and it becomes
  scannable across a hundred rows.
- Uncertainty bands are computed in `FindingsOverlay` only when `Fit + aggregate`
  is toggled. Static views show point estimates with no CI. The existing
  `y_lower/y_upper` in `CurvePoint` is unused on the chart.

If you want the atlas to feel like a serious instrument, the line everywhere
should be: *every quantitative claim on the page is paired with a confidence
chip, a source-strength chip, and a one-click "where did this come from?"
affordance*. Today that's true on detail pages and partly true on `/models`;
it's not yet visible on `/compare` or `/findings`.

---

## Per-page critique

### `/` — home

- The hero `PageHeader` lede is good prose but is the second-densest text on the
  page (max-w-prose paragraph). A research portal home should have ≤1 sentence
  above the chrome, then *show* the data.
- `AtlasOverview` matrix: 10 columns is too many for first-impression value.
  Suggest collapsing into 5 (papers / protocols / datasets / "depth" combined /
  next-action), and re-showing the disaggregated columns when you click into a
  row (it expands inline). Also: the species/modality chip column is
  content-as-decoration; chips wrap unpredictably and add scan complexity.
- `headlineStats` 7-tile bar is informationally identical to `AtlasOverview`'s
  row aggregates. Pick one.
- "Across the literature" — the species table is structurally good but isolated;
  lift it into the matrix or make it a small sparkline strip below the headline.
- "Latest story" Card is right in spirit, wrong in size. A thumbnail (or live
  MiniFindingsChart preview) instead of an empty Card with "→" would do far
  more work.

### `/findings`

- 4 stacked horizontal pill rows above the chart (curve type / stimulus axis /
  presets / Refine accordion + summary + trace mode + Fit toggle) creates a
  vertical staircase before any visualization appears. Consider:
  - merging *curve type* and *stimulus axis* into a single "view" selector with
    a contextual second tier;
  - moving *presets* into a side panel or a `<select>` with thumbnails;
  - making the *summary line* (`X traces · Y papers · Z species`) the page's
    living headline rather than a bottom strip.
- The `<details>` "Browse all findings as a table" at the bottom is a 90-row
  table behind a chevron — invisible to ~all users. Either remove it or
  surface a count/sort/search bar at the top of it so it earns its place.
- The Pyodide *Fit + aggregate* checkbox is the killer feature and currently
  looks like an admin toggle. Consider promoting it to a "Refit live in your
  browser" pill with a small visual cue when Pyodide is loaded vs cold.

### `/models`

- This is the page most in need of progressive disclosure. The
  `SectionAnchorNav` chip cloud has 8 destinations on first paint; the second of
  those (`Model Answers`) is itself a 38KB Svelte browser with its own filter
  UI. The user is pre-overwhelmed.
- "Model Answers" → "Per-finding selection" → "Selection matrix" → "DDM
  cross-species" — the names are internal-engineering. Consider: "Where do the
  data point?", "Where is the call close?", "What's missing?", "Which models
  can which slices support?". Headlines should answer questions.
- The `<details>` blocks (`Comparison-scope reference`, `Interpretation
  warnings`, `DDM fit table`) hide critical glossary content. The scope
  reference in particular should be inline (small definition list under the
  matrix) because scope is the single concept that gates correct interpretation.
- The "Families & variants" section repeats info accessible elsewhere; it could
  be a sidebar glossary that opens when you click a family chip in the matrix,
  rather than a standalone section.
- Caveat tags (`!!`, `! M`) symbols rendered in the live fetch — the symbol
  legend isn't on the page. Always pair symbol with text label inline; add
  legend at top of any table that uses symbols.

### `/compare`

- The "Reading the deltas" Card is a great pattern — top-of-page glossary for
  the page's specific quantities. Replicate this pattern on `/findings` and
  `/models`.
- Each comparison section is a `Card padding="lg"` with chart + (optional) strip
  + model-fit table + parameter-delta table. The vertical rhythm is heavy.
  Consider a tabbed interior (Chart / Models / Parameters) so a reader who only
  wants the chart isn't scrolling past two tables to reach the next comparison.
- The `<a href="#section.id">#</a>` permalink anchor is too subtle
  (opacity-on-hover only via `text-fg-subtle`). Make it visible on hover/focus
  with a clear "copy link" affordance — these are exactly the kind of
  permalinks scientists want to cite.

### `/catalog`

- `CatalogBrowser` is well built but its results are capped at 80 with a
  one-line `Showing first 80 matching records` notice. Either paginate, or
  virtualize, or be louder about the cap (the user with 96 results loses 16
  silently).
- The flat-table `<details>` at the bottom duplicates the family card stack
  above. Remove the duplication; if both views are useful, expose them as a
  toggle (Cards / Table).
- Family Cards stack vertically without thumbnails or visual anchors. Add a
  small protocol-count + dataset-count + slice-count strip-chart per family
  card so scanning down the list actually conveys depth.

### `/slices/[id]`

- Best-shaped detail page in the project. The DetailLayout rail is clean, the
  in-browser Pyodide cell is the right featured action, the artifact list is
  clear.
- Two improvements: (1) Provenance is not visible in the rail — show
  `dataset hash · adapter vN · pipeline run YYYY-MM-DD · commit abc123 ·
  clean/dirty` as a stack near the StatusPill. (2) The `comparison_rows` table
  is good but reads as nine left-labels in a row; turn the label column into a
  `text-eyebrow` style and let the value column breathe.

### `/findings/[id]`

- The most information-dense detail page. The fit-diagnostics table has 9
  columns; on most laptops this requires horizontal scroll. Suggested column
  priority: Variant, AIC, Δ, RMSE, Caveats — collapse `BIC / logL / n / params /
  max abs` into a "more" expander or a per-row drawer.
- `predicted_points` are computed but only used by the residual plot. Consider
  overlaying them as small triangles on the main chart so observed vs predicted
  is visible *before* you scroll to the residual section.
- Citation export in the rail is good. Add an OpenGraph preview image generator
  that includes a thumbnail of the curve — every shared link to a finding should
  show its chart, not the generic /og.svg.

### `/atlas-health`

- This is your operational dashboard, not a scientist-facing page. It belongs on
  a separate route (`/admin` or `/curation`) with reduced visual weight in the
  main nav. Keeping it next to scientific pages dilutes the perceived focus of
  the project.
- The `Gap matrix` at top is genuinely useful for project state. Pull *that one
  component* into a small status banner on the home page ("3 high-priority
  blockers · audit OK · 2 link issues") with a link to the full health page;
  demote everything else.

### `/stories`

- Indexed at three stories with one feature on the home. Stories are the
  highest-leverage place to *show off the atlas* and there's almost no editorial
  scaffolding. A story landing should look like a magazine: cover image (live
  chart thumbnail), one-line dek, byline date, time-to-read estimate. Today
  it's a list of cards with one-line descriptions.
- The visual-contrast story is enormously rich (`CurveGallery`, timeline,
  coverage matrix, model-ambiguity heat) but it's mounted *under*
  `/stories/visual-contrast` — that depth means new readers never reach it. A
  cycling "story of the week" hero on `/` would do more.

### `/graph`

- Force layout with 4 type filters works but has no zoom, pan, search, or
  path-finding. Useful for "is everything connected?", not useful for "find me
  X." Consider replacing with a *layered* layout (4 columns by node type, edges
  as Sankey-like ribbons, node labels always visible at low density and only on
  hover at high density). Add a "find a path between A and B" affordance —
  that's a delight feature for an atlas of relationships.

---

## Accessibility & responsiveness

A short list of the highest-impact gaps; none are catastrophic but the
cumulative effect matters:

1. **Chip / pill state semantics.** Buttons across `FindingsOverlay`, `Nav`,
   `FacetBar`, `ModelAnswersBrowser` use background swaps to denote on/off. Add
   `aria-pressed` (or `role="checkbox" aria-checked`) so AT users can hear
   current state.
2. **Color-only encoding in a few places.** The `CoverageGapMatrix` and the
   source-level 3-segment strip in `AtlasOverview` rely on hue alone. Add a
   redundant glyph (filled/half/empty triangle) or a sr-only label per cell.
   The Vega charts already encode shape on source level — apply the same
   discipline elsewhere.
3. **Heat-map alpha at low end.** `AtlasOverview` heat cells start at
   `rgba(..., 0.1)`. Combined with default text color those cells likely fail
   WCAG AA. Either floor alpha at a higher value or switch to a more
   perceptually-uniform palette and keep text in `text-fg`.
4. **SVG focus indicator.** `RelationshipGraph` nodes have `tabindex="0"` and
   `outline: none`. Add a visible focus ring (e.g., a halo circle that appears
   on `:focus-visible`).
5. **Sticky horizontal-scroll tables.** Wide tables on `/models`,
   `/findings/[id]`, and `/compare` lose their first column off-screen. Add
   `position: sticky; left: 0; background: var(--color-surface-raised);` to the
   first `<th>/<td>` inside `DataTable`.
6. **Reduced motion.** The d3-force simulation in `RelationshipGraph` ticks
   continuously until alpha decays. Wrap the `forceSimulation` in a
   `prefers-reduced-motion: reduce` guard that runs only one tick + uses a
   static layout. Same audit for any Vega `transition`s.
7. **Tooltips as the only carrier of information.**
   `caveatDefinitions[tag]?.description` lives in `title` attributes in many
   places. Move these to inline labels, footnoted glossary cards, or a single
   floating "info" panel that surfaces the definition for whatever the user has
   hovered/focused.
8. **Print stylesheet.** Good as far as it goes, but `<details>` content forces
   open via `display: block`. That works only in some browsers; use
   `[open]`-aware CSS so closed `<details>` collapse to a placeholder citation
   instead of an empty header.

---

## Where delight is missing — and cheap to add

The atlas has more raw delight material than most ML demos. Almost none of it
is presented as a moment of wonder. Some specific suggestions, ordered by
leverage:

1. **Live-fitting hero on `/`.** One curve, one paragraph, "click to refit
   live." When the user clicks, Pyodide loads in the background; the curve
   then animates the new fit and the parameters slide in next to it. This
   single interaction summarizes what the project *is*.
2. **Generative OpenGraph cards.** Render the SVG of each finding's chart at
   build time and embed as the per-page `og:image`. Every shared link to a
   finding becomes a free, accurate preview.
3. **`g f` / `g p` / `g m` keyboard navigation.** Plus `?` for a help overlay
   listing them. Power users build muscle memory; this is a common library to
   lift (e.g., `tinykeys`).
4. **Saved views.** URL state-sync is already done. Add a "★ pin this view"
   button in `FindingsOverlay` that stores the URL in `localStorage` and
   surfaces a "your views" tray on `/findings`. Researchers running comparative
   analyses will use it daily.
5. **Hovering a chip lights up the relationship graph.** Hover a paper chip on
   `/findings/[id]`'s rail, and a small inline graph slice ("paper → 2
   protocols → 3 datasets → 1 slice") appears beside the rail. Cheap with the
   data already on the page; reads as magic.
6. **Distribution-of-thresholds violin.** "Median 75% threshold = 0.27" begs to
   be a violin or strip plot. One small chart. Click a point → goes to that
   finding.
7. **Ambient micro-animations.** When a filter changes, animate the chart traces
   in/out for ~200ms instead of swapping. Vega supports this via `transform`
   updates; today the chart re-mounts.
8. **Empty states with paths forward.** "No matches for 'foo'" → "Try: did you
   mean *RDM*? See *4 papers* matching *macaque visual contrast*." The search
   index already has the data.
9. **Confidence sparkline column.** Replace the textual confidence label in
   `/models` tables with a 4-segment chip `[██░░]` colored by
   `--color-confidence-*`. Scannable across 91 rows.
10. **A "scientific cover sheet" PDF/markdown export per finding.** Printable,
    includes chart, citation, and provenance block. Pairs with `CopyCitation`.

---

## Prioritized roadmap

I'd sequence the work like this. Each level builds on the previous; don't skip
ahead.

**Tier 1 — close the gaps in what's already there (1–2 weeks)**

1. Migrate the remaining `slate-*`/`white`/`bg-emerald-500` literals to encoding
   tokens. Concrete files: `Nav.astro`, `AtlasOverview.astro` (heat-map RGBA,
   source strip), `atlas-health.astro` (the `<details>` and `<article>` chrome),
   the `<style>` block in `AtlasOverview.astro`. Net: about 80 utility-class
   swaps.
2. Add `aria-pressed`/`aria-checked` on every toggleable button; fix
   `RelationshipGraph` focus ring; freeze the first column of `DataTable` when
   it overflows; floor heat-map alpha; pick one underline convention and remove
   the orphan CSS.
3. Add `prefers-reduced-motion` guard to `RelationshipGraph` and any Vega
   transitions.
4. Rename `/graph` to `/network` (or `/map`); move `Atlas health` out of the
   main nav into a footer-level "Project health" link.
5. Pull caveat / confidence / scope definitions out of tooltips into a single
   shared `Glossary.astro` block, used inline at the top of `/models` and
   `/compare` and on each detail page that uses the term.

**Tier 2 — re-orient the home page and the heaviest pages (2–3 weeks)**

6. Rebuild `/` around one hero (story or live-fit demo) + `AtlasOverview`
   collapsed to 5 columns + 1 sparkline strip. Move the build-state aside to a
   footer ribbon.
7. On `/models`, add a one-screen executive summary above `Model Answers`,
   rename sections by question, lift glossary inline, and move
   `Families & variants` and the bottom `All fits` table behind a "Reference"
   tab or `<details>` with a count cue.
8. On `/findings`, merge curve-type + stimulus-axis selectors, demote presets to
   a side affordance, and promote the Pyodide refit toggle.
9. Render per-page OpenGraph SVGs at build time. Update meta in
   `BaseLayout.astro`.
10. Add a 5-node Family→Protocol→Dataset→Slice→Finding mental-model chip strip
    near the top of `/`, `/catalog`, and `/atlas-health`.

**Tier 3 — earn the "standout" descriptor (3–4 weeks)**

11. Saved views (`localStorage` + `URLSearchParams` round-trip).
12. Keyboard navigation system (`g f`, `g p`, `?` help overlay) with `tinykeys`
    or equivalent.
13. Replace `RelationshipGraph` with a layered (column-per-type) layout
    supporting search and "find path between A and B."
14. Pair every quantitative claim with a confidence chip, source-strength chip,
    and a click-to-trace affordance. Add lower-bound/upper-bound bands to
    static curves where `y_lower/y_upper` are present.
15. Ambient micro-animations on filter changes; live-fit hero animation;
    hover-to-light-graph relationship preview on detail page rails.
16. Editorial layer: cycling "story of the week" on `/`, story landing redesigned
    as a magazine grid with thumbnails (live chart + dek + read-time), and a
    per-story navigation bar.

**Tier 4 — features only this project can claim (1+ months, optional)**

17. **In-browser model selection** — let a user point at any two findings,
    choose two model variants, and refit + AIC-rank live. The pieces all exist.
18. **A "what's changed since you last visited" dashboard** keyed off the
    manifest commit hash; surface new findings, new fits, audit-status flips.
19. **Paper-comparison heatmaps** — for any pair of papers, show the overlap of
    their findings on shared evidence axes with delta bars and confidence
    ribbons.
20. **Collaborator's view** — given a slice URL, generate a one-click
    `uv run behavtaskatlas <slice>-report` reproduction recipe with checked-in
    inputs.

---

## Honest summary

Today the site reads as: a serious researcher built a careful, well-curated
YAML store and exposed every artifact as a tab. That's a respectable baseline
and no one is going to mistake it for vibe-coded.

What it isn't yet: a place the rest of the field will want to come back to. To
get there, the work isn't more pages or more features — it's discipline about
*what the user sees first*, ruthless about which things are foreground vs.
reference, and willingness to pick one moment of delight per page and let
everything else recede behind it. The component library, the encoding tokens,
and the data are all already strong enough to support that move; the bottleneck
is editorial.

If I had to pick three changes in priority order: **(1)** finish the
encoding-token migration so the visual surface feels coherent; **(2)** rebuild
`/`, `/models`, and `/findings` around a one-screen executive view with
progressive disclosure underneath; **(3)** invest in story scaffolding and one
live-fit demo so the project's killer feature is the first thing a visitor sees
moving.
