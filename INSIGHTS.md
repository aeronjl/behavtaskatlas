# Insights

This file is the single chronological track of project insights. Add new entries at the top with a local timestamp.

## 2026-04-25 02:56:06 BST - Human visual contrast needs explicit low/high-frequency conventions

The Walsh et al. OSF behavioural stats matrix makes the human visual contrast protocol sliceable without downloading the large raw EEG archives: `1. Behavioural Analysis.mat` contains 66,200 processed behavioural rows across 12 observers, with cue context, pulse type, exposure bin, RT, correctness, difficulty, reward, and lower-frequency response coding.

The technical caveat is important for the atlas: the processed matrix does not preserve raw left/right tilt response or original session ids. The adapter therefore records a transparent canonical convention where `right` means lower-frequency response or target and positive signed contrast means the lower-frequency grating was the target. This keeps the slice comparable while preserving the source-specific convention in `task_variables`.

## 2026-04-25 02:09:46 BST - Human clicks source access is solvable through the page API

The OSF node originally considered for human clicks exposes no API-visible files, but the Mendeley Data page for `Poisson Clicks Task, DBS OFF/ON` does expose its file through the page's own public API: `poisson_clicks_rawdata.mat`, 1.9 MB, CC-BY-4.0, DOI `10.17632/3j86m7mjx2.1`. That lets the human auditory-clicks protocol become a real vertical slice instead of a source-access blocker.

The implementation lesson is that source-access adapters may need to model repository-specific discovery paths, not just published public APIs. The resulting slice maps source `cdiff` from left-minus-right into the atlas right-minus-left axis, uses only pre-response click times for the evidence kernel, and preserves full scheduled click trains in `task_variables` for auditability.

## 2026-04-25 01:50:59 BST - Human RDM turns cross-species comparison into a first-class slice

The human random-dot motion button reaction-time protocol now has a CoSMo2017-backed Palmer-Huk-Shadlen vertical slice. The same RDM analysis surface can compare macaque saccade RDM and human button-response RDM while preserving distinct provenance, response modality, and signed-coherence conventions.

This removes both queue items for the human RDM protocol and drops the curation queue to six open items. The implementation lesson is that shared task families need adapters that are specific about source coding, especially here where CoSMo2017 preprocessed the original data, assigned zero-coherence choices, and uses a rightward zero-coherence convention for correctness reconstruction.

## 2026-04-25 00:44:45 BST - TrainingChoiceWorld adds a fourth report-backed slice

The mouse unbiased visual contrast wheel protocol now has a concrete OpenAlyx `trainingChoiceWorld` session selected, harmonized, analyzed, and reported. This turns the broad IBL public behavior dataset link into an analysis-ready slice for one pinned session while preserving the distinction between archive coverage and the exact subset used for a report.

The curation impact is measurable: the atlas now has four report-backed concrete protocols, and the queue drops to eight open items. The deeper technical lesson is that protocol variants need lightweight adapters around shared canonical trial semantics, because this training session uses the same contrast-choice structure as the IBL visual decision slice but different behavioral context through `probabilityLeft` and task protocol metadata.

## 2026-04-25 00:29:52 BST - Broad datasets can back catalog variants before slice subsets are pinned

The mouse unbiased visual contrast wheel protocol is now linked to the broad IBL public behavioral dataset. This is justified as metadata because IBL public behavior includes training-phase choice-world data, and IBL tooling distinguishes `trainingChoiceWorld` from biased and ephys choice-world sessions.

The atlas should still treat this as incomplete for analysis: the broad dataset link removes the `needs dataset` queue item, but the protocol keeps its `needs vertical slice` item until a concrete unbiased-session subset is selected and reported. This is the right granularity for early curation, where broad archive coverage and analysis-ready subsets are different commitments.

## 2026-04-25 00:25:32 BST - Protocol templates need different QA pressure from concrete variants

Protocols now declare whether they are abstract `template` records or concrete executable records. The rat auditory-clicks protocol points back to the generic Poisson clicks template with `template_protocol_id`, and the relationship graph exports a protocol-variant edge between them.

This changes the curation semantics: concrete protocols should be pushed toward datasets and vertical slices, while templates should organize task families and variants without being treated as missing their own report-backed analysis. The queue can now shrink for the right reason instead of demanding a redundant slice for an intentionally abstract record.

## 2026-04-24 23:30:34 BST - Concrete slices should attach to concrete protocols

The auditory-clicks report-backed slice now points to the concrete rat nose-poke protocol rather than the generic Poisson clicks protocol. The harmonizer stamps generated canonical trials with the same concrete protocol id, so the analysis artifact, slice metadata, and protocol catalog now agree about what task instance was actually analyzed.

This did not reduce the queue numerically, because the generic Poisson clicks protocol now honestly carries the remaining `needs vertical slice` item. That is useful signal: the atlas needs an explicit way to represent abstract protocol templates versus concrete executable protocol variants, rather than relying on the presence of one report-backed concrete slice to satisfy both records.

## 2026-04-24 23:11:40 BST - Queue items should shrink through reciprocal metadata

The first curation-queue reduction linked the concrete rat auditory-clicks nose-poke protocol to the Brody Lab parsed Poisson Clicks dataset, and added the reciprocal protocol id back to the dataset record. This removes one `needs dataset` item while preserving the separate `needs vertical slice` item for that protocol.

That distinction matters for the MVP: linking a known dataset should be lightweight metadata work, while adding a report-backed slice remains a deeper analysis commitment. The queue can therefore track incremental open-science progress without forcing every useful curation action to become a full vertical slice immediately.

## 2026-04-24 23:06:32 BST - Graph QA should become a curation queue

The relationship graph now has enough structure to generate a contributor-facing worklist. Turning QA issues into `curation_queue.html` and `curation_queue.json` makes incompleteness operational: protocol records without datasets and protocols without vertical slices become grouped action items rather than passive warnings.

This is the next step in making the atlas useful for open science. It gives future contributors a stable surface for choosing what to curate next while preserving the file-first architecture: committed records generate graph QA, graph QA generates the queue, and no backend workflow system is required for the MVP.

## 2026-04-24 22:49:33 BST - Reciprocal links turn QA into a cleaner curation signal

The classic macaque random-dot motion protocol now explicitly declares the Roitman-Shadlen PyDDM dataset that already listed it. That removes the graph QA warning for a missing reciprocal protocol-dataset link while preserving the informational gaps for catalog-only protocols that do not yet have linked datasets or report-backed slices.

This is the intended QA behavior: structural inconsistencies should be fixable metadata work, while breadth records without deep slices remain visible as future curation opportunities rather than failures.

## 2026-04-24 21:58:49 BST - Graph QA should surface curation gaps, not block breadth

The relationship graph now includes a QA section in both HTML and JSON. It flags orphan records, missing reciprocal protocol-dataset links, protocols without linked datasets, protocols without report-backed slices, and datasets without report-backed slices, with severity levels so expected breadth gaps can remain informational while structural asymmetries appear as warnings.

This matches the atlas contribution model: lightweight catalog-only protocols are useful and should not fail validation, but they should be visible as incomplete. The graph QA turns incompleteness into a curated worklist rather than hiding it in the record files.

## 2026-04-24 21:49:40 BST - The atlas graph is now an exported artifact

The static build now writes `derived/graph.html` and `derived/graph.json` from the same catalog payload as the table and detail pages. The graph has typed nodes for task families, protocols, datasets, and vertical slices, plus typed edges for family-protocol, family-slice, protocol-dataset, protocol-slice, and dataset-slice relationships.

This makes the atlas network first-class without adding infrastructure. HTML supports inspection, while JSON gives future tooling a stable graph-shaped contract for search, visualization, QA checks, and eventual API or database loading.

## 2026-04-24 21:22:47 BST - Dataset pages complete the first task-data loop

The static catalog now writes one detail page per dataset and links dataset rows plus protocol-page dataset references into those pages. Dataset pages expose source access, license, data formats, expected trial-table mapping, linked protocols, linked report-backed slices, references, provenance, and caveats.

This closes the first browse loop in the MVP: a user can move from catalog search to protocol structure, from protocol to dataset, and from dataset back to linked protocols and reports. That is the minimum useful graph for an atlas rather than a flat list of records.

## 2026-04-24 21:08:31 BST - Protocol records need inspectable pages

The generated catalog now writes one static detail page per protocol and links each protocol table row to that page. The detail pages expose the richer protocol metadata that was already present in YAML: description, stimulus and choice structure, timing phases, linked datasets, report-backed slices, expected analyses, interpretive claims, references, provenance, and open questions.

This is an important product step for the MVP because search and filters help users find candidate tasks, but inspectable protocol pages are what make the catalog feel citable and curatable. It also keeps the architecture file-first: the same committed records generate the browse table, machine-readable JSON, and human-readable protocol pages.

## 2026-04-24 20:52:48 BST - Static catalog browsing is enough for the MVP

The catalog HTML now has dependency-free protocol browsing: text search plus filters for species, modality, evidence type, and report status. This keeps the MVP deployable as static files while making the breadth catalog usable as it grows beyond the three report-backed slices.

The product implication is that the atlas does not need a backend search service yet. The committed YAML records can generate both a machine-readable JSON catalog and a self-contained HTML catalog, while heavier infrastructure can wait until there are enough records, users, and curation workflows to justify it.

## 2026-04-24 20:37:42 BST - Catalog-only protocols test breadth without reports

The catalog now includes six lightweight protocol records without vertical slices: human visual contrast 2AFC, mouse unbiased visual contrast wheel, human RDM button reaction-time, macaque RDM confidence wagering, human auditory clicks button, and rat auditory clicks nose-poke. Repository validation now sees 18 records total, while the generated catalog separates 9 protocol records from 3 report-backed vertical slices.

This is the first realistic test of the breadth/depth split. The catalog can now show meaningful protocol coverage even when a record has no linked dataset or report, and it labels those entries as `no slice` rather than hiding them. That is the behavior needed for community curation: many task records can be useful before they become fully analysis-backed.

## 2026-04-24 20:29:17 BST - Catalog generation connects breadth to depth

The static build now writes `derived/catalog.html` and `derived/catalog.json` alongside the report index and manifest. The catalog is generated from committed task-family, protocol, dataset, and vertical-slice records, then overlays local report availability from ignored `derived/` artifacts. This gives the MVP a breadth surface: lightweight records can appear in the atlas before they have a full vertical slice, while completed slices still link through to their deeper reports.

The design implication is that future growth should separate two contribution paths. A contributor can add a curated task/protocol/dataset record to improve catalog coverage, or add a vertical slice to make that catalog entry analysis-backed. The catalog is the bridge between those levels.

## 2026-04-24 20:13:53 BST - Slice comparison metadata becomes curated data

Vertical-slice comparison metadata now lives in `vertical_slices/*/slice.yaml` rather than inside the static-index renderer. Each slice record declares its family, protocol, dataset, artifact paths, display order, and comparable fields such as species, modality, evidence type, response modality, analysis outputs, data scope, and canonical axis. Repository validation now treats these as first-class records and checks their cross-references plus controlled vocabulary values.

The generated `derived/manifest.json` also has a committed JSON schema. This is a useful architectural step: the atlas surface is no longer just an HTML convenience page, and downstream tooling can consume the same manifest contract that the local report index renders.

## 2026-04-24 19:28:13 BST - The static index becomes an atlas surface

The local `site-index` output now has two roles: `derived/index.html` is a human-readable comparison surface, and `derived/manifest.json` is the machine-readable manifest for the same generated reports and artifacts. Each vertical slice declares a normalized comparison row with family, protocol, dataset, species, modality, stimulus metric, evidence type, response modality, analysis outputs, data scope, canonical axis, report status, artifact status, and primary link.

This is the first step from separate report demos toward an atlas. The important design choice is to keep the comparison fields close to the slice payloads rather than deriving them ad hoc from generated HTML. Future slices should add one explicit comparison block, then the index and manifest can update without hand-editing a separate page.

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
