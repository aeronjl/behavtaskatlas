<script lang="ts">
  import FacetBar from "./FacetBar.svelte";

  type LinkedRecord = {
    name?: string | null;
    title?: string | null;
    dataset_id?: string | null;
    protocol_id?: string | null;
    slice_id?: string | null;
    source_data_level?: string | null;
  };

  type PaperBrowserRow = {
    authors?: string[] | null;
    bibtex: string;
    citation: string;
    coverage_status: string;
    curation_status?: string | null;
    curve_types?: string[] | null;
    datasets?: LinkedRecord[] | null;
    doi?: string | null;
    finding_count: number;
    finding_n_subjects_max?: number | null;
    id: string;
    lab?: string | null;
    model_fit_count?: number | null;
    n_subjects?: number | null;
    notes?: string | null;
    protocols?: LinkedRecord[] | null;
    ris: string;
    slug: string;
    source_data_levels?: string[] | null;
    species?: string[] | null;
    total_n_trials?: number;
    url?: string | null;
    venue?: string | null;
    vertical_slices?: LinkedRecord[] | null;
    year: number;
  };

  type FacetKey = "coverage" | "species" | "source" | "curve" | "protocol";

  let { rows }: { rows: PaperBrowserRow[] } = $props();

  const coverageLabels: Record<string, string> = {
    findings: "Findings extracted",
    "analysis-linked": "Analysis linked",
    "data-linked": "Dataset linked",
    "protocol-linked": "Protocol curated",
    "bibliography-only": "Bibliography only",
  };

  const sourceStateLabels: Record<string, string> = {
    all: "All source states",
    linked: "Has source data",
    missing: "No source data yet",
  };

  const sortLabels: Record<string, string> = {
    "newest": "Newest first",
    "oldest": "Oldest first",
    "findings-desc": "Most findings",
    "trials-desc": "Most trials",
    "subjects-desc": "Most subjects",
    "citation-asc": "Citation A-Z",
  };

  const facetParam: Record<FacetKey, string> = {
    coverage: "coverage",
    species: "species",
    source: "source",
    curve: "curve",
    protocol: "protocol",
  };

  function slugForId(id: string | undefined): string {
    return (id ?? "").replace(/^[^.]+\./, "");
  }

  function fmtCount(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return "-";
    return value.toLocaleString();
  }

  function subjectCount(row: PaperBrowserRow): number | null {
    return row.n_subjects ?? row.finding_n_subjects_max ?? null;
  }

  function sliceCount(row: PaperBrowserRow): number {
    return row.vertical_slices?.length ?? 0;
  }

  function datasetCount(row: PaperBrowserRow): number {
    return row.datasets?.length ?? 0;
  }

  function modelFitCount(row: PaperBrowserRow): number {
    return row.model_fit_count ?? 0;
  }

  function readable(value: string): string {
    if (value === "non-human-primate") return "NHP";
    if (value === "processed-trial") return "processed trials";
    if (value === "raw-trial") return "raw trials";
    if (value === "figure-source-data") return "figure source data";
    return value.replace(/[_-]/g, " ");
  }

  function coverageLabel(value: string): string {
    return coverageLabels[value] ?? readable(value);
  }

  function dataHref(mime: string, text: string): string {
    return `data:${mime};charset=utf-8,${encodeURIComponent(text)}`;
  }

  function filteredHref(path: string, param: string, value: string): string {
    return `${path}?${param}=${encodeURIComponent(value)}`;
  }

  function paperQuery(row: PaperBrowserRow): string {
    return row.citation.split(".")[0] ?? row.slug;
  }

  function valueText(values: readonly string[] | undefined): string {
    return values && values.length > 0 ? values.map(readable).join(", ") : "-";
  }

  function stripWidth(value: number | null | undefined, max: number): string {
    if (!value || max <= 0) return "0%";
    return `${Math.max(8, Math.round((value / max) * 100))}%`;
  }

  function sourceClass(level: string): string {
    if (level === "raw-trial") return "bg-encoding-source-raw";
    if (level === "processed-trial") return "bg-encoding-source-processed";
    if (level === "figure-source-data") return "bg-encoding-source-figure";
    return "bg-rule-strong";
  }

  function curveClass(curve: string): string {
    if (curve === "psychometric") return "bg-encoding-curve-psychometric";
    if (curve === "chronometric") return "bg-encoding-curve-chronometric";
    if (curve === "accuracy_by_strength") return "bg-encoding-curve-accuracy";
    return "bg-fg-muted";
  }

  function coverageTone(status: string): string {
    if (status === "findings") return "bg-encoding-coverage-findings";
    if (status === "analysis-linked") return "bg-encoding-coverage-analysis";
    if (status === "data-linked") return "bg-encoding-coverage-data";
    if (status === "protocol-linked") return "bg-encoding-coverage-protocol";
    return "bg-encoding-coverage-bibliography";
  }

  function coverageStepClass(active: boolean, tone: string): string {
    return active ? tone : "bg-surface-sunken";
  }

  type Option = { value: string; label: string; count: number };

  function optionCounts(
    getValues: (row: PaperBrowserRow) => readonly string[] | undefined,
    labelFor = readable,
  ): Option[] {
    const counts = new Map<string, number>();
    for (const row of rows) {
      for (const value of getValues(row) ?? []) {
        counts.set(value, (counts.get(value) ?? 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .map(([value, count]) => ({ value, label: labelFor(value), count }))
      .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  }

  const options: Record<FacetKey, Option[]> = {
    coverage: optionCounts((row) => [row.coverage_status], coverageLabel),
    species: optionCounts((row) => row.species),
    source: optionCounts((row) => row.source_data_levels),
    curve: optionCounts((row) => row.curve_types),
    protocol: optionCounts(
      (row) => row.protocols?.map((protocol) => protocol.name ?? protocol.protocol_id ?? ""),
      (value) => value,
    ),
  };

  const allowedValues: Record<FacetKey, Set<string>> = {
    coverage: new Set(options.coverage.map((option) => option.value)),
    species: new Set(options.species.map((option) => option.value)),
    source: new Set(options.source.map((option) => option.value)),
    curve: new Set(options.curve.map((option) => option.value)),
    protocol: new Set(options.protocol.map((option) => option.value)),
  };

  function initialParam(name: string): string | null {
    if (typeof window === "undefined") return null;
    return new URLSearchParams(window.location.search).get(name);
  }

  function initialSet(key: FacetKey): Set<string> {
    const raw = initialParam(facetParam[key]);
    if (!raw) return new Set();
    const allowed = allowedValues[key];
    return new Set(
      raw
        .split(",")
        .map((value) => value.trim())
        .filter((value) => allowed.has(value)),
    );
  }

  const initialSort = initialParam("sort") ?? "newest";
  const initialSourceState = initialParam("source_state") ?? "all";

  let query = $state(initialParam("q") ?? "");
  let sortMode = $state(sortLabels[initialSort] ? initialSort : "newest");
  let sourceState = $state(
    sourceStateLabels[initialSourceState] ? initialSourceState : "all",
  );
  let selected = $state<Record<string, Set<string>>>({
    coverage: initialSet("coverage"),
    species: initialSet("species"),
    source: initialSet("source"),
    curve: initialSet("curve"),
    protocol: initialSet("protocol"),
  });

  const facets = $derived([
    { key: "coverage", label: "Coverage", options: options.coverage },
    { key: "species", label: "Species", options: options.species },
    { key: "source", label: "Source level", options: options.source },
    { key: "curve", label: "Curve type", options: options.curve },
    { key: "protocol", label: "Protocol", options: options.protocol },
  ]);

  const sortOptions = Object.entries(sortLabels).map(([value, label]) => ({
    value,
    label,
  }));
  const stateOptions = Object.entries(sourceStateLabels).map(([value, label]) => ({
    value,
    label,
  }));

  const presets = [
    { key: "findings", label: "with findings" },
    { key: "needs-extraction", label: "needs extraction" },
    { key: "visual", label: "visual tasks" },
    { key: "rdm-clicks", label: "RDM / clicks" },
    { key: "human", label: "human" },
    { key: "mouse", label: "mouse" },
  ];

  const activeFilterCount = $derived(
    (selected.coverage?.size ?? 0) +
      (selected.species?.size ?? 0) +
      (selected.source?.size ?? 0) +
      (selected.curve?.size ?? 0) +
      (selected.protocol?.size ?? 0) +
      (sourceState === "all" ? 0 : 1) +
      (query.trim().length > 0 ? 1 : 0),
  );

  function setFacetValues(key: FacetKey, values: string[]) {
    const allowed = allowedValues[key];
    selected = {
      ...selected,
      [key]: new Set(values.filter((value) => allowed.has(value))),
    };
  }

  function resetFilters() {
    query = "";
    sortMode = "newest";
    sourceState = "all";
    selected = {
      coverage: new Set(),
      species: new Set(),
      source: new Set(),
      curve: new Set(),
      protocol: new Set(),
    };
  }

  function applyPreset(preset: string) {
    resetFilters();
    if (preset === "findings") {
      setFacetValues("coverage", ["findings"]);
      sortMode = "findings-desc";
    }
    if (preset === "needs-extraction") {
      setFacetValues("coverage", ["protocol-linked", "bibliography-only"]);
    }
    if (preset === "human") {
      setFacetValues("species", ["human"]);
    }
    if (preset === "mouse") {
      setFacetValues("species", ["mouse"]);
    }
    if (preset === "visual") {
      const visualProtocols = options.protocol
        .map((option) => option.value)
        .filter((value) => value.toLowerCase().includes("visual"));
      setFacetValues("protocol", visualProtocols);
    }
    if (preset === "rdm-clicks") {
      const accumulationProtocols = options.protocol
        .map((option) => option.value)
        .filter((value) => {
          const lower = value.toLowerCase();
          return lower.includes("random-dot motion") || lower.includes("click");
        });
      setFacetValues("protocol", accumulationProtocols);
    }
  }

  $effect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    if (query.trim().length > 0) params.set("q", query.trim());
    if (sortMode !== "newest") params.set("sort", sortMode);
    if (sourceState !== "all") params.set("source_state", sourceState);
    for (const key of Object.keys(facetParam) as FacetKey[]) {
      const set = selected[key] ?? new Set<string>();
      const arr = Array.from(set).sort();
      if (arr.length > 0) params.set(facetParam[key], arr.join(","));
    }
    const search = params.toString();
    const next = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(null, "", next);
    }
  });

  function includesAny(values: readonly string[] | undefined, set: Set<string>): boolean {
    if (set.size === 0) return true;
    return (values ?? []).some((value) => set.has(value));
  }

  function paperHaystack(row: PaperBrowserRow): string {
    return [
      row.id,
      row.citation,
      row.venue,
      row.lab,
      row.doi,
      row.notes,
      ...(row.authors ?? []),
      ...(row.species ?? []),
      ...(row.source_data_levels ?? []),
      ...(row.curve_types ?? []),
      ...(row.protocols ?? []).map((protocol) => protocol.name ?? protocol.protocol_id ?? ""),
      ...(row.datasets ?? []).map((dataset) => dataset.name ?? dataset.dataset_id ?? ""),
      ...(row.vertical_slices ?? []).map((slice) => slice.title ?? slice.slice_id ?? ""),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
  }

  function matchesQuery(row: PaperBrowserRow, q: string): boolean {
    const tokens = q
      .toLowerCase()
      .split(/\s+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0);
    if (tokens.length === 0) return true;
    const haystack = paperHaystack(row);
    return tokens.every((token) => haystack.includes(token));
  }

  function rowMatches(row: PaperBrowserRow): boolean {
    if (!matchesQuery(row, query.trim())) return false;
    if (
      (selected.coverage?.size ?? 0) > 0 &&
      !(selected.coverage as Set<string>).has(row.coverage_status)
    ) {
      return false;
    }
    if (!includesAny(row.species, selected.species ?? new Set())) return false;
    if (!includesAny(row.source_data_levels, selected.source ?? new Set())) return false;
    if (!includesAny(row.curve_types, selected.curve ?? new Set())) return false;
    if (
      !includesAny(
        row.protocols?.map((protocol) => protocol.name ?? protocol.protocol_id ?? ""),
        selected.protocol ?? new Set(),
      )
    ) {
      return false;
    }
    if (sourceState === "linked" && (row.source_data_levels ?? []).length === 0) {
      return false;
    }
    if (sourceState === "missing" && (row.source_data_levels ?? []).length > 0) {
      return false;
    }
    return true;
  }

  function sorted(rowsToSort: PaperBrowserRow[]): PaperBrowserRow[] {
    return rowsToSort.slice().sort((a, b) => {
      if (sortMode === "oldest") return a.year - b.year || a.citation.localeCompare(b.citation);
      if (sortMode === "findings-desc") {
        return b.finding_count - a.finding_count || b.year - a.year;
      }
      if (sortMode === "trials-desc") {
        return (b.total_n_trials ?? 0) - (a.total_n_trials ?? 0) || b.year - a.year;
      }
      if (sortMode === "subjects-desc") {
        return (subjectCount(b) ?? 0) - (subjectCount(a) ?? 0) || b.year - a.year;
      }
      if (sortMode === "citation-asc") return a.citation.localeCompare(b.citation);
      return b.year - a.year || a.citation.localeCompare(b.citation);
    });
  }

  const sortedBaseRows = $derived(
    rows.slice().sort((a, b) => b.year - a.year || a.citation.localeCompare(b.citation)),
  );

  const filteredRows = $derived(sorted(sortedBaseRows.filter(rowMatches)));
  const maxFindings = $derived(Math.max(1, ...rows.map((row) => row.finding_count ?? 0)));
  const maxModels = $derived(Math.max(1, ...rows.map(modelFitCount)));
  const maxSlices = $derived(Math.max(1, ...rows.map(sliceCount)));

  const summary = $derived.by(() => {
    const protocols = new Set<string>();
    let findings = 0;
    let modelFits = 0;
    let slices = 0;
    let trials = 0;
    let sourceLinked = 0;
    for (const row of filteredRows) {
      findings += row.finding_count;
      modelFits += modelFitCount(row);
      slices += sliceCount(row);
      trials += row.total_n_trials ?? 0;
      if ((row.source_data_levels ?? []).length > 0) sourceLinked += 1;
      for (const protocol of row.protocols ?? []) {
        protocols.add(protocol.name ?? protocol.protocol_id ?? "");
      }
    }
    return { findings, modelFits, slices, trials, protocols: protocols.size, sourceLinked };
  });
</script>

<section class="space-y-4">
  <FacetBar
    searchPlaceholder="paper, lab, protocol, dataset, DOI"
    bind:query
    {sortOptions}
    bind:sortMode
    sortLabel="Sort"
    {stateOptions}
    bind:stateMode={sourceState}
    stateLabel="Source state"
    {presets}
    onPreset={applyPreset}
    {facets}
    bind:selected
    {activeFilterCount}
    onClearAll={resetFilters}
  />

  <div class="flex flex-col gap-2 text-body text-fg-secondary sm:flex-row sm:items-center sm:justify-between">
    <p>
      Showing <span class="font-mono font-semibold text-fg">{filteredRows.length}</span>
      of <span class="font-mono text-fg">{rows.length}</span> papers ·
      <span class="font-mono text-fg">{fmtCount(summary.findings)}</span> findings ·
      <span class="font-mono text-fg">{fmtCount(summary.modelFits)}</span> model fits ·
      <span class="font-mono text-fg">{fmtCount(summary.slices)}</span> slices ·
      <span class="font-mono text-fg">{fmtCount(summary.trials)}</span> trials ·
      <span class="font-mono text-fg">{summary.protocols}</span> protocols
    </p>
    <p class="text-body-xs text-fg-muted">
      {summary.sourceLinked} source-linked paper{summary.sourceLinked === 1 ? "" : "s"}
    </p>
  </div>

  {#if filteredRows.length === 0}
    <section class="rounded-md border border-rule bg-surface-raised p-6 text-body text-fg-secondary">
      <p>No papers match the current filters.</p>
      {#if activeFilterCount > 0}
        <button
          type="button"
          class="mt-3 rounded border border-rule-strong bg-surface px-2 py-1 text-body-xs font-semibold text-fg hover:border-rule-emphasis hover:text-accent"
          onclick={resetFilters}
        >
          Clear filters
        </button>
      {/if}
    </section>
  {:else}
    <ul class="grid grid-cols-1 gap-3 lg:grid-cols-2">
      {#each filteredRows as row (row.id)}
        <li class="flex min-w-0 flex-col rounded-md border border-rule bg-surface-raised p-4">
          <header class="flex min-w-0 items-start justify-between gap-3">
            <div class="min-w-0">
              <h2 class="text-body-lg font-semibold leading-snug">
                <a class="text-fg no-underline hover:text-accent" href={`/papers/${row.slug}`}>
                  {row.citation}
                </a>
              </h2>
              <p class="mt-1 break-all font-mono text-mono-id text-fg-muted">{row.id}</p>
            </div>
            <span class="shrink-0 rounded bg-surface-sunken px-2 py-0.5 text-body-xs text-fg-secondary">
              {row.year}
            </span>
          </header>

          <div class="mt-3 flex flex-wrap gap-1 text-mono-id">
            <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">
              {coverageLabel(row.coverage_status)}
            </span>
            {#if row.lab}
              <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">{row.lab}</span>
            {/if}
            {#each row.species ?? [] as species (species)}
              <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">{readable(species)}</span>
            {/each}
          </div>

          <div
            data-testid="paper-coverage-strip"
            class="mt-3 rounded-md border border-rule bg-surface p-3"
            aria-label={`${paperQuery(row)} coverage strip`}
          >
            <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-6">
              <div class="xl:col-span-2">
                <div class="mb-1 flex items-baseline justify-between gap-2">
                  <span class="text-eyebrow uppercase text-fg-muted">Coverage</span>
                  <span class="text-mono-id text-fg-secondary">{coverageLabel(row.coverage_status)}</span>
                </div>
                <div
                  class="grid grid-cols-6 gap-1"
                  title="bibliography, protocol, source, slice, finding, model coverage"
                >
                  <span class="h-2 rounded-full bg-surface0" title="bibliography curated"></span>
                  <span
                    class={["h-2 rounded-full", coverageStepClass((row.protocols?.length ?? 0) > 0, "bg-encoding-coverage-protocol")]}
                    title={`${row.protocols?.length ?? 0} linked protocol${(row.protocols?.length ?? 0) === 1 ? "" : "s"}`}
                  ></span>
                  <span
                    class={["h-2 rounded-full", coverageStepClass((row.source_data_levels?.length ?? 0) > 0, "bg-encoding-coverage-data")]}
                    title={`${row.source_data_levels?.length ?? 0} source level${(row.source_data_levels?.length ?? 0) === 1 ? "" : "s"}`}
                  ></span>
                  <span
                    class={["h-2 rounded-full", coverageStepClass(sliceCount(row) > 0, "bg-encoding-coverage-analysis")]}
                    title={`${sliceCount(row)} linked slice${sliceCount(row) === 1 ? "" : "s"}`}
                  ></span>
                  <span
                    class={["h-2 rounded-full", coverageStepClass(row.finding_count > 0, "bg-encoding-coverage-findings")]}
                    title={`${row.finding_count} extracted finding${row.finding_count === 1 ? "" : "s"}`}
                  ></span>
                  <span
                    class={["h-2 rounded-full", coverageStepClass(modelFitCount(row) > 0, "bg-encoding-model-ddm")]}
                    title={`${modelFitCount(row)} model fit${modelFitCount(row) === 1 ? "" : "s"}`}
                  ></span>
                </div>
              </div>

              <a
                class="no-underline"
                href={filteredHref("/findings", "q", paperQuery(row))}
                title={`${row.finding_count} extracted finding${row.finding_count === 1 ? "" : "s"}`}
              >
                <span class="flex items-baseline justify-between gap-2">
                  <span class="text-eyebrow uppercase text-fg-muted">Findings</span>
                  <span class="font-mono text-body-xs text-fg">{row.finding_count}</span>
                </span>
                <span class="mt-1 block h-1.5 rounded-full bg-surface-raised">
                  <span
                    class={["block h-1.5 rounded-full", coverageTone(row.coverage_status)]}
                    style={`width: ${stripWidth(row.finding_count, maxFindings)}`}
                  ></span>
                </span>
              </a>

              <a
                class="no-underline"
                href={filteredHref("/models", "model_q", paperQuery(row))}
                title={`${modelFitCount(row)} committed model fit${modelFitCount(row) === 1 ? "" : "s"}`}
              >
                <span class="flex items-baseline justify-between gap-2">
                  <span class="text-eyebrow uppercase text-fg-muted">Models</span>
                  <span class="font-mono text-body-xs text-fg">{modelFitCount(row)}</span>
                </span>
                <span class="mt-1 block h-1.5 rounded-full bg-surface-raised">
                  <span
                    class="block h-1.5 rounded-full bg-encoding-model-ddm"
                    style={`width: ${stripWidth(modelFitCount(row), maxModels)}`}
                  ></span>
                </span>
              </a>

              <a
                class="no-underline"
                href={`/papers/${row.slug}`}
                title={`${sliceCount(row)} linked slice${sliceCount(row) === 1 ? "" : "s"} and ${datasetCount(row)} linked dataset${datasetCount(row) === 1 ? "" : "s"}`}
              >
                <span class="flex items-baseline justify-between gap-2">
                  <span class="text-eyebrow uppercase text-fg-muted">Slices</span>
                  <span class="font-mono text-body-xs text-fg">{sliceCount(row)}</span>
                </span>
                <span class="mt-1 block h-1.5 rounded-full bg-surface-raised">
                  <span
                    class="block h-1.5 rounded-full bg-encoding-coverage-analysis"
                    style={`width: ${stripWidth(sliceCount(row), maxSlices)}`}
                  ></span>
                </span>
              </a>

              <div>
                <div class="mb-1 flex items-baseline justify-between gap-2">
                  <span class="text-eyebrow uppercase text-fg-muted">Curves</span>
                  <span class="font-mono text-body-xs text-fg">{row.curve_types?.length ?? 0}</span>
                </div>
                <div class="flex gap-1" title={valueText(row.curve_types)}>
                  {#if row.curve_types && row.curve_types.length > 0}
                    {#each row.curve_types as curve (curve)}
                      <span class={["h-2 flex-1 rounded-full", curveClass(curve)]} title={readable(curve)}></span>
                    {/each}
                  {:else}
                    <span class="h-2 flex-1 rounded-full bg-surface-sunken" title="no curves extracted"></span>
                  {/if}
                </div>
              </div>

              <div>
                <div class="mb-1 flex items-baseline justify-between gap-2">
                  <span class="text-eyebrow uppercase text-fg-muted">Source</span>
                  <span class="font-mono text-body-xs text-fg">{row.source_data_levels?.length ?? 0}</span>
                </div>
                <div class="flex gap-1" title={valueText(row.source_data_levels)}>
                  {#if row.source_data_levels && row.source_data_levels.length > 0}
                    {#each row.source_data_levels as level (level)}
                      <span class={["h-2 flex-1 rounded-full", sourceClass(level)]} title={readable(level)}></span>
                    {/each}
                  {:else}
                    <span class="h-2 flex-1 rounded-full bg-surface-sunken" title="no linked source data"></span>
                  {/if}
                </div>
              </div>
            </div>
          </div>

          <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-body-xs text-fg-secondary sm:grid-cols-4">
            <div>
              <dt class="text-fg-muted">Findings</dt>
              <dd class="font-mono font-semibold text-fg">{row.finding_count}</dd>
            </div>
            <div>
              <dt class="text-fg-muted">Trials</dt>
              <dd class="font-mono font-semibold text-fg">{fmtCount(row.total_n_trials)}</dd>
            </div>
            <div>
              <dt class="text-fg-muted">Subjects</dt>
              <dd class="font-mono font-semibold text-fg">{fmtCount(subjectCount(row))}</dd>
            </div>
            <div>
              <dt class="text-fg-muted">Curves</dt>
              <dd>{valueText(row.curve_types)}</dd>
            </div>
          </dl>

          <div class="mt-3 space-y-2 text-body-xs text-fg-secondary">
            <div>
              <p class="font-semibold text-fg-muted">Protocols</p>
              {#if row.protocols && row.protocols.length > 0}
                <ul class="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                  {#each row.protocols as protocol (protocol.protocol_id ?? protocol.name)}
                    <li>
                      {#if protocol.protocol_id}
                        <a class="text-accent" href={`/protocols/${slugForId(protocol.protocol_id)}`}>
                          {protocol.name ?? protocol.protocol_id}
                        </a>
                      {:else}
                        {protocol.name}
                      {/if}
                    </li>
                  {/each}
                </ul>
              {:else}
                <p class="mt-1 text-fg-muted">-</p>
              {/if}
            </div>

            <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div>
                <p class="font-semibold text-fg-muted">Source levels</p>
                <p class="mt-1">{valueText(row.source_data_levels)}</p>
              </div>
              <div>
                <p class="font-semibold text-fg-muted">Slices</p>
                {#if row.vertical_slices && row.vertical_slices.length > 0}
                  <ul class="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                    {#each row.vertical_slices as slice (slice.slice_id ?? slice.title)}
                      <li>
                        {#if slice.slice_id}
                          <a class="text-accent" href={`/slices/${slugForId(slice.slice_id)}`}>
                            {slice.title ?? slice.slice_id}
                          </a>
                        {:else}
                          {slice.title}
                        {/if}
                      </li>
                    {/each}
                  </ul>
                {:else}
                  <p class="mt-1 text-fg-muted">-</p>
                {/if}
              </div>
            </div>
          </div>

          <div class="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-4 text-body-xs">
            <a class="font-semibold text-accent" href={`/papers/${row.slug}`}>Details</a>
            {#if row.doi}
              <a class="text-accent" href={`https://doi.org/${row.doi}`}>doi:{row.doi}</a>
            {:else if row.url}
              <a class="text-accent" href={row.url}>source</a>
            {/if}
            <a
              class="text-fg-secondary hover:text-accent"
              download={`${row.slug}.bib`}
              href={dataHref("application/x-bibtex", row.bibtex)}
            >
              BibTeX
            </a>
            <a
              class="text-fg-secondary hover:text-accent"
              download={`${row.slug}.ris`}
              href={dataHref("application/x-research-info-systems", row.ris)}
            >
              RIS
            </a>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
