# Insights

This file is the single chronological track of project insights. Add new entries at the top with a local timestamp.

## 2026-04-24 19:15:36 BST - Random-dot motion completes the third report-backed slice

The Roitman-Shadlen random-dot motion slice now runs end to end from a pinned PyDDM processed CSV. The local pipeline downloads a 132,610 byte CSV with SHA256 `7ac2daa16e9631aa189ae146a89f9f29cc6fccd6c0f31b4d5849990a6cebbd4b`, harmonizes 6,149 trials across `monkey-1` and `monkey-2`, writes 11 signed-coherence psychometric rows, writes 6 absolute-coherence chronometric rows, and renders `derived/random_dot_motion/roitman-shadlen-pyddm/report.html`.

This exposes a useful representation problem for the atlas: the processed CSV preserves target identity but not stable screen side. The slice therefore maps target 1/target 2 onto canonical right/left labels only as a comparison convention, while preserving the original values in `task_variables`. That pattern is likely important for other classic tasks where the scientifically meaningful variable is not cleanly identical to a generic left/right field.

With `site-index` regenerated, the MVP now has three report-available vertical slices: auditory clicks, IBL visual decision, and random-dot motion. The next impactful step is not another static report, but a cross-slice comparison page or shared artifact manifest that makes these three reports act like one atlas rather than three isolated examples.

## 2026-04-24 18:52:05 BST - IBL now has the same report surface as auditory clicks

The IBL visual-decision slice now has `ibl-report`, which renders `derived/ibl_visual_decision/ebce500b-c530-47de-8cb1-963c552703ea/report.html` from the existing analysis result, provenance, and psychometric SVG. The report summarizes 569 trials, 537 response trials, 32 no-response trials, three prior blocks, the selected OpenAlyx revision, the session metadata for `MFD_09`, the fitted prior-block psychometrics, and the psychometric summary rows.

After regenerating `site-index`, both current vertical slices are report-available. This is a meaningful threshold for the MVP: the project no longer has one polished scientific page plus one hidden analysis artifact. It has a repeatable pattern for turning each deep slice into a comparable local report page.

## 2026-04-24 18:42:03 BST - A local static index connects vertical slices

The MVP now has a small static site entry point. `site-index` writes `derived/index.html`, currently indexing two vertical slices: auditory clicks has a complete report link, while IBL visual decision is marked as analysis-artifacts available and report pending. This gives the generated outputs a navigable local surface without changing the policy that `derived/` remains ignored.

The useful pattern is a report-status card per slice rather than a hand-built page. Future slices can move through states: metadata only, analysis artifacts available, report available. That state model should make it easier to scale the atlas from one impressive slice to multiple comparable slices without pretending they are equally mature.

## 2026-04-24 18:33:48 BST - Static reports make ignored local artifacts inspectable

The auditory-clicks slice now has a dependency-free static report command. `clicks-report` reads the ignored local aggregate JSON and SVG artifacts, then writes `derived/auditory_clicks/report.html` with top-level metrics, coverage/provenance, an inline evidence-kernel plot, per-rat coverage, per-rat/gamma psychometric bias rows, aggregate kernel rows, artifact links, and caveats.

This is an important MVP pattern: raw files and generated derived artifacts can remain out of git while the codebase still defines a reproducible inspection surface. The report is not yet the public site, but it is the smallest credible unit of a scientific atlas page: task metadata, data provenance, result summaries, a figure, and links back to machine-readable outputs.

## 2026-04-24 18:24:01 BST - Clicks batch aggregate turns local artifacts into a miniature dataset

The auditory-clicks slice now has an aggregate layer that reads existing batch outputs rather than reprocessing raw `.mat` files. `clicks-aggregate` uses `derived/auditory_clicks/batch_summary.csv` plus each rat's generated `analysis_result.json` and `evidence_kernel_result.json`, then writes `aggregate_psychometric_bias.csv`, `aggregate_kernel_summary.csv`, `aggregate_result.json`, and `aggregate_kernel.svg`.

The first aggregate run over `A080`, `B075`, `B127`, `T014`, and `T074` found 5 ok batch rows, 0 failed rows, 0 artifact errors, 61,222 total parsed trials, 44 per-rat/gamma psychometric bias rows, and 10 aggregate evidence-kernel bins. The cross-rat kernel is positive in every normalized time bin: mean choice-triggered evidence is 0.92 clicks in the first bin and about 1.4 clicks in later bins. This is still descriptive rather than a hierarchical model, but it makes the MVP feel less like isolated examples and more like a regenerable miniature task dataset.

## 2026-04-24 18:10:17 BST - Batch clicks ingestion tests archive variation

The clicks pipeline now has a batch mode that runs harmonization, psychometric analysis, and evidence-kernel analysis for multiple local rat `.mat` files, then writes `derived/auditory_clicks/batch_summary.csv`. The first batch used five of the smallest extracted files: `A080.mat`, `B075.mat`, `B127.mat`, `T014.mat`, and `T074.mat`.

All five batch files were `location` task files and processed successfully: 61,222 total parsed trials, 1,551 total psychometric summary rows, 10 evidence-kernel rows per rat, and zero evidence-kernel exclusions. The batch surfaced real archive variation in gamma schedules (`B075` uses integer gammas, while other small files use half-step gammas), which confirms the value of keeping prior context as a label rather than hard-coding a fixed set of task blocks.

## 2026-04-24 17:50:18 BST - First task-specific analysis uses preserved click times

The auditory-clicks slice now exercises `task_variables` for more than storage. `clicks-analyze` writes a descriptive evidence kernel from `task_variables.left_click_times`, `task_variables.right_click_times`, and `task_variables.stimulus_duration`, binning each trial into 10 normalized stimulus-time bins and summarizing signed evidence as right-minus-left clicks.

For `B075.mat`, all 11,285 parsed trials are included in the kernel. The output is deliberately labeled as a choice-triggered descriptive kernel: each bin reports mean signed evidence, right-choice and left-choice means, their difference, a point-biserial correlation with choice, and a normalized weight. This is useful as the first task-specific analysis artifact, but it should not be interpreted as a full accumulation-model or multivariate click-weighting fit.

## 2026-04-24 17:42:04 BST - Psychometric analysis should be canonical but labelled per task

The IBL and auditory-clicks slices now share a canonical two-choice psychometric analysis path over `stimulus_value`, `choice`, `correct`, `prior_context`, and response availability. The common machinery should stay task-agnostic, but each slice must supply scientifically meaningful labels and metric names: IBL reports signed contrast, while auditory clicks reports signed click-count difference.

For `B075.mat`, the baseline clicks analysis reads 11,285 canonical trials and writes a psychometric summary, JSON result, and SVG plot. The fitted per-gamma results are deliberately descriptive: they use a four-parameter logistic binomial fit over click-count difference and do not yet model within-trial click timing. The next slice-specific scientific step is a click-time weighting or evidence-kernel analysis using the preserved `task_variables.left_click_times` and `task_variables.right_click_times`.

## 2026-04-24 17:29:24 BST - Real auditory-clicks archive validates the second slice

The Brody Lab Zenodo archive downloads cleanly as an 8,104,686,746 byte file, but it uses ZIP64 plus Deflate64 compression. macOS `unzip`, `ditto`, `bsdtar`, and Python `zipfile` cannot reliably extract it; `7z` from Homebrew `p7zip` works. This should be treated as a local tooling requirement for raw-data work, not as a runtime dependency of the atlas package.

The first real smoke run used the smallest rat file, `B075.mat`, extracted under ignored `data/raw/brody_clicks/extracted/`. Its `ratdata.parsed` struct contains 11,285 parsed `location` trials. The clicks adapter harmonized all 11,285 trials and produced 181 summary rows under ignored `derived/auditory_clicks/B075-parsed/`. The real file confirmed the value of `task_variables`: click counts, signed click difference, stimulus duration, gamma, reward gamma, task type, and left/right click-time vectors all remain machine-readable without bloating the canonical top-level schema.

## 2026-04-24 16:59:41 BST - Download large auditory-clicks archive locally

The Brody Lab Poisson Clicks archive is large but acceptable to download locally for MVP development. Raw archives and extracted source files should remain ignored under `data/raw/`, while derived canonical outputs remain under `derived/`. This lets the second vertical slice move beyond fixture-only adapter tests and exercise a real rat-level `.mat` file from Zenodo without committing bulky source data to git.

## 2026-04-24 16:54:16 BST - Add task-specific variables before second slice

Before starting the auditory-clicks vertical slice, the canonical trial representation should gain a `task_variables` dictionary for structured task-specific values. This keeps the cross-task core compact while allowing task families to store meaningful variables such as click counts, click rates, event-derived evidence, or stimulus-generation parameters without bloating the top-level schema.

The design rule is that task variables should be machine-readable, namespaced by the adapter or task family where needed, and used for analyses only when their semantics are documented in the slice's source-field mapping.

## 2026-04-24 16:52:03 BST - IBL slice now pins table revision and fits psychometrics

The IBL vertical slice now loads `_ibl_trials.table.pqt` directly instead of the broader `trials` object, selects the OpenAlyx default table revision, and records the selected revision, dataset id, hash, file size, and QC status in provenance. For the first verified session this pins revision `2025-03-03`, dataset id `91928c8f-8278-47d9-bc69-a4805d3924ec`, hash `0c404a34978db3eaad31198f162ae693`, and QC `PASS`.

The analysis output now includes fitted four-parameter logistic psychometric estimates per prior block using binomial likelihood over response trials. The summary denominator has been tightened: `p_right` is computed from response trials, while no-response trials remain visible in `n_trials` and `n_no_response`. This makes the first slice more credible as a reusable scientific pipeline while still labeling the fit as a pragmatic MVP model rather than the full IBL psychofit implementation.

## 2026-04-24 16:39:09 BST - IBL analysis exposed and fixed choice-code convention

The first analysis pass exposed an important convention error in the initial IBL adapter: IBL `choice` codes should be mapped as `1` left, `-1` right, and `0` no response for this task representation. The previous mapping inverted p(right), which made the psychometric summary run in the wrong direction. The adapter, tests, source-field documentation, and derived local outputs have been corrected.

The IBL slice now includes a descriptive analysis command that reads the canonical trial CSV and emits a psychometric summary, empirical bias/threshold/lapse estimates, an analysis JSON file, and a dependency-free SVG psychometric plot. These remain generated under ignored `derived/` until data release policy is settled.

## 2026-04-24 16:26:05 BST - Next phase is data policy plus first analysis output

The first real-data IBL slice now works end to end, so the next bottleneck is no longer ingestion. The next phase should decide whether derived trial tables can be committed, and in parallel add the first analysis artifact generated from the ignored local trial table: a psychometric-ready summary and ideally a simple plot or structured result file.

The highest-value next step is to turn the IBL slice from "harmonized data exists locally" into "the atlas can reproduce and inspect a behavioral result." That means formalizing derived-data policy, tightening source-revision provenance, adding a baseline psychometric analysis command, and deciding what result artifacts should be tracked in git versus regenerated locally.

## 2026-04-24 16:22:49 BST - First real IBL harmonization succeeded

The first real-data pass uses OpenAlyx session `ebce500b-c530-47de-8cb1-963c552703ea` from `churchlandlab_ucla`, subject `MFD_09`, start time `2023-10-19T12:54:25.961859`, task protocol `_iblrig_tasks_ephysChoiceWorld`. The session loads a small `_ibl_trials.table.pqt` and harmonizes to 569 canonical trial rows.

The generated baseline summary has 27 rows grouped by signed contrast and prior context. Initial provenance counts are 32 no-response trials, 0 missing-stimulus trials, and 0 missing-response-time trials. Generated artifacts are kept under ignored `derived/` until IBL data licensing, source revision handling, and release policy are settled.

This validates the vertical-slice architecture: task protocol metadata, dataset metadata, source-field mapping, canonical trial schema, adapter code, summary generation, and provenance can now be exercised end to end on one real session.

## 2026-04-24 16:10:52 BST - First IBL slice starts at the adapter boundary

The first IBL visual decision vertical slice should begin at the adapter boundary rather than by downloading a large dataset. The implemented slice now records the source trial fields, defines a canonical trial representation, and provides a tested adapter from IBL ALF trial fields to that canonical form.

This establishes the key transformation assumptions early: `contrastRight` maps to positive signed contrast, `contrastLeft` maps to negative signed contrast, `choice` values map to right/left/no-response, `feedbackType` maps to correctness and reward/error feedback, `response_times - stimOn_times` is the initial response-time definition, and `probabilityLeft` is preserved as prior context. The next slice step is to select one small public session and run this adapter on a real `_ibl_trials.table.pqt` or ONE-loaded trials object.

## 2026-04-24 16:00:43 BST - Working name and implementation defaults accepted

The working project name is **behavtaskatlas**. The accepted MVP defaults are YAML-authored records, Python validation tooling, Pydantic-style schemas, `uv` for local Python workflow, strict identifiers/provenance/vocabularies, permissive handling of complex task details, IBL visual decision as the first deep vertical slice, and three initial exemplar tasks: IBL visual decision, random-dot motion discrimination, and auditory click/evidence accumulation.

The next implementation step is to create a buildable repository scaffold with schemas, vocabularies, seed records, and validation before expanding the catalog.

## 2026-04-24 15:58:27 BST - Defer hosting and start with MVP foundations

Hosting and deployment should be deferred while the MVP proves its core scientific and technical structure. The next phase should focus on the file-first foundations: schemas, controlled vocabularies, exemplar task records, validation tooling, and one first vertical slice that connects a task record to dataset metadata and analysis expectations.

The immediate work should proceed in dependency order: stabilize the object model, draft the first schema, create three high-quality exemplar task records, build validation, then expand only after the schema has been tested against real task variation.

## 2026-04-24 15:55:40 BST - Hosting should separate publication, computation, and storage

The preferred MVP hosting architecture should separate the public catalog from scientific computation. A static site on Cloudflare Pages or Workers static assets can serve the catalog, while Python validation and analysis jobs run in CI or batch environments and publish derived artifacts. Cloudflare R2 is a good fit for exported JSON, harmonized trial tables, figures, and release artifacts; D1 or a prebuilt search index can be added only when static filtering becomes insufficient.

Although Cloudflare Python Workers now provide a first-class Python experience, they should not be the first home for heavier scientific Python workloads such as pandas/scipy/model fitting. Request-time Workers are better suited to APIs, search, redirects, metadata lookup, and small validation endpoints. The MVP should remain file-first and rebuildable from git.

## 2026-04-24 15:51:29 BST - Technical depth is in representation, not the website

The deeper implementation challenge is not building a catalog interface; it is designing representations that make tasks comparable without flattening away scientifically important differences. The MVP needs stable identifiers, schema versioning, provenance, validation, ontology boundaries, task-family inheritance, trial-table harmonization, executable or semi-executable task specifications, and reproducible analysis outputs.

The core technical problem is to connect four levels cleanly: abstract task family, concrete protocol, dataset/session/trial data, and model or analysis result. If these levels are conflated, the atlas becomes ambiguous. If they are separated too rigidly, contribution becomes too burdensome. The MVP should therefore use pragmatic files and schemas first, while leaving room for a graph model and formal ontology later.

Immediate technical design decisions should focus on identifiers, schema evolution, controlled vocabularies, task inheritance, temporal/event representation, data adapters, validation tooling, and provenance of derived analyses.

## 2026-04-24 15:48:53 BST - MVP should prove vertical usefulness

The MVP should not optimize only for the number of cataloged tasks. It should prove a complete user path: a researcher can discover a task family, inspect its operational variables, compare variants, find linked data, run or inspect baseline analyses, and understand how to contribute a better record.

The most persuasive MVP shape is therefore a hybrid of breadth and depth: 30-50 lightly curated task records for map coverage, plus 3-5 deeply curated vertical slices with schema-complete task records, linked open data, harmonized trial tables, generated psychometric/chronometric summaries, and documented provenance. This prevents the project from becoming a static bibliography while keeping the first release achievable.

Key decisions now include the exact anchor task families, whether the first release prioritizes rodents only or cross-species comparison, the minimum required fields for a task record, the canonical trial-table format, the treatment of cognitive labels as claims rather than facts, and whether the first public surface should be a static site, a Python package plus docs, or both.

## 2026-04-24 15:45:51 BST - Initial project framing

The proposed enterprise is feasible, but the impactful version should be more than a repository of psychometric tasks. The stronger project is a **task atlas for behavioral neuroscience**: a machine-readable map linking task design, trial-level data, implementations, protocols, and model fits.

The analogy to Tim Vogels' ion-channel database is useful because the value comes from classification plus quantitative comparison. In this project, tasks should not merely be listed; they should be described through comparable variables such as modality, stimulus statistics, evidence structure, choice geometry, action mapping, feedback and reward rules, timing, priors, blocks, training regimes, apparatus, species, and common variants.

The current ecosystem appears strong on adjacent infrastructure but weak on this exact object. Relevant neighbors include Cognitive Atlas for cognitive task concepts, OpenBehavior for behavioral tools, NWB/DANDI/BIDS/HED for data and event standards, and IBL as a proof that standardized decision tasks plus open data can work across laboratories. The gap is a task-centered, cross-species, comparative database for sensory and decision paradigms.

The project should be built in layers:

1. **Task ontology**: operational task variables first, interpretive cognitive claims second.
2. **Trial-level data layer**: harmonized behavioral trial tables, with raw neural data linked rather than duplicated where possible.
3. **Analysis and model layer**: standard psychometric, chronometric, history-dependent, GLM, drift-diffusion, reinforcement-learning, and ideal-observer fits.
4. **Executable task layer**: reference implementations or links for PsychoPy, jsPsych, Bonsai, pyControl, Bpod, and related systems.
5. **Comparison interface**: ways to search for similar tasks, contrast variants, and identify available datasets or fitted models.

The recommended MVP should be narrow: sensory-guided decision-making tasks in rodents, primates, and humans. A first target of 30-50 canonical tasks is plausible, including random-dot motion, contrast discrimination, auditory clicks, vibrotactile flutter, go/no-go detection, the IBL visual decision task, evidence-accumulation tasks, confidence/report tasks, and dynamic foraging-style variants.

The hard parts are curation, incentives, and ontology discipline rather than software alone. The project will be most transformative if it helps laboratories before publication: choosing tasks, reporting them cleanly, depositing data, and comparing new experiments against known task families.
