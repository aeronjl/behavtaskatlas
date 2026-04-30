<script lang="ts">
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

  type Option = {
    value: string;
    label: string;
    count: number;
  };

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

  const sortedBaseRows = $derived(
    rows.slice().sort((a, b) => b.year - a.year || a.citation.localeCompare(b.citation)),
  );

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

  function valueText(values: readonly string[] | undefined): string {
    return values && values.length > 0 ? values.map(readable).join(", ") : "-";
  }

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
  let activeCoverage = $state(initialSet("coverage"));
  let activeSpecies = $state(initialSet("species"));
  let activeSource = $state(initialSet("source"));
  let activeCurve = $state(initialSet("curve"));
  let activeProtocol = $state(initialSet("protocol"));

  const activeSets = $derived({
    coverage: activeCoverage,
    species: activeSpecies,
    source: activeSource,
    curve: activeCurve,
    protocol: activeProtocol,
  });

  const activeFilterCount = $derived(
    activeCoverage.size +
      activeSpecies.size +
      activeSource.size +
      activeCurve.size +
      activeProtocol.size +
      (sourceState === "all" ? 0 : 1) +
      (query.trim().length > 0 ? 1 : 0),
  );

  function selectedSet(key: FacetKey): Set<string> {
    return activeSets[key];
  }

  function setSelected(key: FacetKey, next: Set<string>) {
    if (key === "coverage") activeCoverage = next;
    if (key === "species") activeSpecies = next;
    if (key === "source") activeSource = next;
    if (key === "curve") activeCurve = next;
    if (key === "protocol") activeProtocol = next;
  }

  function syncUrl() {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    if (query.trim().length > 0) params.set("q", query.trim());
    if (sortMode !== "newest") params.set("sort", sortMode);
    if (sourceState !== "all") params.set("source_state", sourceState);
    for (const key of Object.keys(facetParam) as FacetKey[]) {
      const selected = Array.from(selectedSet(key)).sort();
      if (selected.length > 0) params.set(facetParam[key], selected.join(","));
    }
    const search = params.toString();
    const next = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(null, "", next);
    }
  }

  function toggleFacet(key: FacetKey, value: string) {
    const next = new Set(selectedSet(key));
    if (next.has(value)) next.delete(value);
    else next.add(value);
    setSelected(key, next);
    syncUrl();
  }

  function clearFacet(key: FacetKey) {
    setSelected(key, new Set());
    syncUrl();
  }

  function resetFilters() {
    query = "";
    sortMode = "newest";
    sourceState = "all";
    activeCoverage = new Set();
    activeSpecies = new Set();
    activeSource = new Set();
    activeCurve = new Set();
    activeProtocol = new Set();
  }

  function clearAll() {
    resetFilters();
    syncUrl();
  }

  function updateQuery(event: Event) {
    query = (event.currentTarget as HTMLInputElement).value;
    syncUrl();
  }

  function updateSourceState(event: Event) {
    sourceState = (event.currentTarget as HTMLSelectElement).value;
    syncUrl();
  }

  function updateSortMode(event: Event) {
    sortMode = (event.currentTarget as HTMLSelectElement).value;
    syncUrl();
  }

  function setFacetValues(key: FacetKey, values: string[]) {
    const allowed = allowedValues[key];
    setSelected(key, new Set(values.filter((value) => allowed.has(value))));
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
    syncUrl();
  }

  function includesAny(values: readonly string[] | undefined, selected: Set<string>): boolean {
    if (selected.size === 0) return true;
    return (values ?? []).some((value) => selected.has(value));
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
    if (activeCoverage.size > 0 && !activeCoverage.has(row.coverage_status)) return false;
    if (!includesAny(row.species, activeSpecies)) return false;
    if (!includesAny(row.source_data_levels, activeSource)) return false;
    if (!includesAny(row.curve_types, activeCurve)) return false;
    if (
      !includesAny(
        row.protocols?.map((protocol) => protocol.name ?? protocol.protocol_id ?? ""),
        activeProtocol,
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

  const filteredRows = $derived(sorted(sortedBaseRows.filter(rowMatches)));

  const summary = $derived.by(() => {
    const protocols = new Set<string>();
    let findings = 0;
    let trials = 0;
    let sourceLinked = 0;
    for (const row of filteredRows) {
      findings += row.finding_count;
      trials += row.total_n_trials ?? 0;
      if ((row.source_data_levels ?? []).length > 0) sourceLinked += 1;
      for (const protocol of row.protocols ?? []) {
        protocols.add(protocol.name ?? protocol.protocol_id ?? "");
      }
    }
    return { findings, trials, protocols: protocols.size, sourceLinked };
  });
</script>

<section class="space-y-4">
  <div class="rounded-md border border-slate-200 bg-white p-4">
    <div class="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1.8fr)_minmax(11rem,0.75fr)_minmax(11rem,0.75fr)]">
      <label class="text-xs text-slate-600">
        <span class="mb-1 block font-semibold text-slate-700">Search</span>
        <input
          value={query}
          oninput={updateQuery}
          type="search"
          class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          placeholder="paper, lab, protocol, dataset, DOI"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
        />
      </label>
      <label class="text-xs text-slate-600">
        <span class="mb-1 block font-semibold text-slate-700">Source state</span>
        <select
          value={sourceState}
          onchange={updateSourceState}
          class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
        >
          {#each Object.entries(sourceStateLabels) as [value, label] (value)}
            <option value={value}>{label}</option>
          {/each}
        </select>
      </label>
      <label class="text-xs text-slate-600">
        <span class="mb-1 block font-semibold text-slate-700">Sort</span>
        <select
          value={sortMode}
          onchange={updateSortMode}
          class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
        >
          {#each Object.entries(sortLabels) as [value, label] (value)}
            <option value={value}>{label}</option>
          {/each}
        </select>
      </label>
    </div>

    <div class="mt-3 flex flex-wrap gap-2 text-xs">
      <button
        type="button"
        class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent"
        onclick={() => applyPreset("findings")}
      >
        with findings
      </button>
      <button
        type="button"
        class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent"
        onclick={() => applyPreset("needs-extraction")}
      >
        needs extraction
      </button>
      <button
        type="button"
        class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent"
        onclick={() => applyPreset("visual")}
      >
        visual tasks
      </button>
      <button
        type="button"
        class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent"
        onclick={() => applyPreset("rdm-clicks")}
      >
        RDM / clicks
      </button>
      <button
        type="button"
        class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent"
        onclick={() => applyPreset("human")}
      >
        human
      </button>
      <button
        type="button"
        class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent"
        onclick={() => applyPreset("mouse")}
      >
        mouse
      </button>
      {#if activeFilterCount > 0}
        <button
          type="button"
          class="rounded border border-slate-300 bg-slate-50 px-2 py-1 font-semibold text-slate-800 hover:border-accent hover:text-accent"
          onclick={clearAll}
        >
          clear {activeFilterCount}
        </button>
      {/if}
    </div>

    <div class="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-5">
      {#each Object.entries(options) as [key, facetOptions] (key)}
        <div class="min-w-0">
          <div class="mb-1 flex items-center justify-between gap-2 text-xs">
            <h2 class="font-semibold text-slate-700">
              {key === "coverage" ? "Coverage" : key === "source" ? "Source level" : key === "curve" ? "Curve type" : key === "protocol" ? "Protocol" : "Species"}
            </h2>
            {#if selectedSet(key as FacetKey).size > 0}
              <button
                type="button"
                class="text-slate-500 hover:text-accent"
                onclick={() => clearFacet(key as FacetKey)}
              >
                all
              </button>
            {/if}
          </div>
          <div class="flex max-h-36 flex-wrap gap-1 overflow-y-auto pr-1">
            {#each facetOptions as option (option.value)}
              {@const selected = selectedSet(key as FacetKey).has(option.value)}
              <button
                type="button"
                class={[
                  "max-w-full rounded border px-2 py-0.5 text-left text-[11px]",
                  selected
                    ? "border-accent bg-accent text-white"
                    : "border-slate-300 bg-white text-slate-700 hover:border-accent hover:text-accent",
                ]}
                onclick={() => toggleFacet(key as FacetKey, option.value)}
              >
                <span class="inline-block max-w-[15rem] truncate align-bottom">{option.label}</span>
                <span class={["ml-1 font-mono", selected ? "text-white" : "text-slate-500"]}>
                  {option.count}
                </span>
              </button>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  </div>

  <div class="flex flex-col gap-2 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
    <p>
      Showing <span class="font-mono font-semibold text-slate-900">{filteredRows.length}</span>
      of <span class="font-mono text-slate-900">{rows.length}</span> papers ·
      <span class="font-mono text-slate-900">{fmtCount(summary.findings)}</span> findings ·
      <span class="font-mono text-slate-900">{fmtCount(summary.trials)}</span> trials ·
      <span class="font-mono text-slate-900">{summary.protocols}</span> protocols
    </p>
    <p class="text-xs text-slate-500">
      {summary.sourceLinked} source-linked paper{summary.sourceLinked === 1 ? "" : "s"}
    </p>
  </div>

  {#if filteredRows.length === 0}
    <section class="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600">
      <p>No papers match the current filters.</p>
      {#if activeFilterCount > 0}
        <button
          type="button"
          class="mt-3 rounded border border-slate-300 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-800 hover:border-accent hover:text-accent"
          onclick={clearAll}
        >
          Clear filters
        </button>
      {/if}
    </section>
  {:else}
    <ul class="grid grid-cols-1 gap-3 lg:grid-cols-2">
      {#each filteredRows as row (row.id)}
        <li class="flex min-w-0 flex-col rounded-md border border-slate-200 bg-white p-4">
          <header class="flex min-w-0 items-start justify-between gap-3">
            <div class="min-w-0">
              <h2 class="text-base font-semibold leading-snug">
                <a class="text-slate-900 no-underline hover:text-accent" href={`/papers/${row.slug}`}>
                  {row.citation}
                </a>
              </h2>
              <p class="mt-1 break-all font-mono text-xs text-slate-500">{row.id}</p>
            </div>
            <span class="shrink-0 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
              {row.year}
            </span>
          </header>

          <div class="mt-3 flex flex-wrap gap-1 text-[11px]">
            <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">
              {coverageLabel(row.coverage_status)}
            </span>
            {#if row.lab}
              <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{row.lab}</span>
            {/if}
            {#each row.species ?? [] as species (species)}
              <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{readable(species)}</span>
            {/each}
          </div>

          <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs text-slate-700 sm:grid-cols-4">
            <div>
              <dt class="text-slate-500">Findings</dt>
              <dd class="font-mono font-semibold text-slate-900">{row.finding_count}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Trials</dt>
              <dd class="font-mono font-semibold text-slate-900">{fmtCount(row.total_n_trials)}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Subjects</dt>
              <dd class="font-mono font-semibold text-slate-900">{fmtCount(subjectCount(row))}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Curves</dt>
              <dd>{valueText(row.curve_types)}</dd>
            </div>
          </dl>

          <div class="mt-3 space-y-2 text-xs text-slate-700">
            <div>
              <p class="font-semibold text-slate-500">Protocols</p>
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
                <p class="mt-1 text-slate-500">-</p>
              {/if}
            </div>

            <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <div>
                <p class="font-semibold text-slate-500">Source levels</p>
                <p class="mt-1">{valueText(row.source_data_levels)}</p>
              </div>
              <div>
                <p class="font-semibold text-slate-500">Slices</p>
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
                  <p class="mt-1 text-slate-500">-</p>
                {/if}
              </div>
            </div>
          </div>

          <div class="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-4 text-xs">
            <a class="font-semibold text-accent" href={`/papers/${row.slug}`}>Details</a>
            {#if row.doi}
              <a class="text-accent" href={`https://doi.org/${row.doi}`}>doi:{row.doi}</a>
            {:else if row.url}
              <a class="text-accent" href={row.url}>source</a>
            {/if}
            <a
              class="text-slate-600 hover:text-accent"
              download={`${row.slug}.bib`}
              href={dataHref("application/x-bibtex", row.bibtex)}
            >
              BibTeX
            </a>
            <a
              class="text-slate-600 hover:text-accent"
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
