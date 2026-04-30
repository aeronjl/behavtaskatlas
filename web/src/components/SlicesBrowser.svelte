<script lang="ts">
  type SliceMetric = {
    label: string;
    value: unknown;
  };

  type SliceComparison = {
    analysis_outputs?: string | null;
    canonical_axis?: string | null;
    choice_type?: string | null;
    data_scope?: string | null;
    evidence_type?: string | null;
    modality?: string | null;
    response_modality?: string | null;
    source_data_level?: string | null;
    species?: string | null;
    stimulus_metric?: string | null;
  };

  type SliceRow = {
    artifact_status?: string | null;
    comparison: SliceComparison;
    dataset_id: string;
    dataset_name?: string | null;
    description?: string | null;
    family_id: string;
    family_name?: string | null;
    id: string;
    metrics?: SliceMetric[] | null;
    primary_link?: string | null;
    primary_link_label?: string | null;
    protocol_id: string;
    protocol_name?: string | null;
    report_status?: string | null;
    status_label?: string | null;
    title: string;
  };

  type FacetKey = "family" | "species" | "modality" | "evidence" | "source";

  type Option = {
    value: string;
    label: string;
    count: number;
  };

  let { rows }: { rows: SliceRow[] } = $props();

  const sortLabels: Record<string, string> = {
    "title-asc": "Title A-Z",
    "trials-desc": "Most trials",
    "findings-desc": "Most output rows",
    "report-first": "Reports first",
    "family-asc": "Family A-Z",
  };

  const statusLabels: Record<string, string> = {
    all: "All report states",
    available: "Report available",
    missing: "Report missing",
  };

  const facetParam: Record<FacetKey, string> = {
    family: "family",
    species: "species",
    modality: "modality",
    evidence: "evidence",
    source: "source",
  };

  function slugForId(id: string | undefined): string {
    return (id ?? "").replace(/^[^.]+\./, "");
  }

  function readable(value: string | null | undefined): string {
    if (!value) return "-";
    if (value === "non-human-primate") return "NHP";
    if (value === "processed-trial") return "processed trials";
    if (value === "raw-trial") return "raw trials";
    if (value === "figure-source-data") return "figure source data";
    return value.replace(/[_-]/g, " ");
  }

  function fmt(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return "-";
    return value.toLocaleString();
  }

  function metricValue(row: SliceRow, pattern: RegExp): number {
    const metric = (row.metrics ?? []).find((m) => pattern.test(m.label));
    return typeof metric?.value === "number" ? metric.value : 0;
  }

  function trialCount(row: SliceRow): number {
    return metricValue(row, /trial/i);
  }

  function outputCount(row: SliceRow): number {
    return metricValue(row, /row|point|bin|session|image/i);
  }

  function valuesFor(row: SliceRow, key: FacetKey): string[] {
    if (key === "family") return [row.family_name || row.family_id].filter(Boolean);
    if (key === "species") return [row.comparison.species ?? ""].filter(Boolean);
    if (key === "modality") return [row.comparison.modality ?? ""].filter(Boolean);
    if (key === "evidence") return [row.comparison.evidence_type ?? ""].filter(Boolean);
    return [row.comparison.source_data_level ?? ""].filter(Boolean);
  }

  function optionCounts(key: FacetKey, labelFor = readable): Option[] {
    const counts = new Map<string, number>();
    for (const row of rows) {
      for (const value of valuesFor(row, key)) {
        counts.set(value, (counts.get(value) ?? 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .map(([value, count]) => ({ value, label: labelFor(value), count }))
      .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  }

  const options: Record<FacetKey, Option[]> = {
    family: optionCounts("family", (value) => value),
    species: optionCounts("species"),
    modality: optionCounts("modality"),
    evidence: optionCounts("evidence"),
    source: optionCounts("source"),
  };

  const allowedValues: Record<FacetKey, Set<string>> = {
    family: new Set(options.family.map((option) => option.value)),
    species: new Set(options.species.map((option) => option.value)),
    modality: new Set(options.modality.map((option) => option.value)),
    evidence: new Set(options.evidence.map((option) => option.value)),
    source: new Set(options.source.map((option) => option.value)),
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

  const initialSort = initialParam("sort") ?? "title-asc";
  const initialStatus = initialParam("report") ?? "all";

  let query = $state(initialParam("q") ?? "");
  let sortMode = $state(sortLabels[initialSort] ? initialSort : "title-asc");
  let statusMode = $state(statusLabels[initialStatus] ? initialStatus : "all");
  let activeFamily = $state(initialSet("family"));
  let activeSpecies = $state(initialSet("species"));
  let activeModality = $state(initialSet("modality"));
  let activeEvidence = $state(initialSet("evidence"));
  let activeSource = $state(initialSet("source"));

  const activeSets = $derived({
    family: activeFamily,
    species: activeSpecies,
    modality: activeModality,
    evidence: activeEvidence,
    source: activeSource,
  });

  const activeFilterCount = $derived(
    activeFamily.size +
      activeSpecies.size +
      activeModality.size +
      activeEvidence.size +
      activeSource.size +
      (statusMode === "all" ? 0 : 1) +
      (query.trim().length > 0 ? 1 : 0),
  );

  function selectedSet(key: FacetKey): Set<string> {
    return activeSets[key];
  }

  function setSelected(key: FacetKey, next: Set<string>) {
    if (key === "family") activeFamily = next;
    if (key === "species") activeSpecies = next;
    if (key === "modality") activeModality = next;
    if (key === "evidence") activeEvidence = next;
    if (key === "source") activeSource = next;
  }

  function syncUrl() {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    if (query.trim().length > 0) params.set("q", query.trim());
    if (sortMode !== "title-asc") params.set("sort", sortMode);
    if (statusMode !== "all") params.set("report", statusMode);
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
    sortMode = "title-asc";
    statusMode = "all";
    activeFamily = new Set();
    activeSpecies = new Set();
    activeModality = new Set();
    activeEvidence = new Set();
    activeSource = new Set();
  }

  function clearAll() {
    resetFilters();
    syncUrl();
  }

  function setFacetValues(key: FacetKey, values: string[]) {
    const allowed = allowedValues[key];
    setSelected(key, new Set(values.filter((value) => allowed.has(value))));
  }

  function applyPreset(preset: string) {
    resetFilters();
    if (preset === "reports") statusMode = "available";
    if (preset === "missing") statusMode = "missing";
    if (preset === "visual") setFacetValues("modality", ["visual"]);
    if (preset === "auditory") setFacetValues("modality", ["auditory"]);
    if (preset === "processed") setFacetValues("source", ["processed-trial"]);
    if (preset === "mouse") setFacetValues("species", ["mouse"]);
    syncUrl();
  }

  function updateQuery(event: Event) {
    query = (event.currentTarget as HTMLInputElement).value;
    syncUrl();
  }

  function updateStatus(event: Event) {
    statusMode = (event.currentTarget as HTMLSelectElement).value;
    syncUrl();
  }

  function updateSort(event: Event) {
    sortMode = (event.currentTarget as HTMLSelectElement).value;
    syncUrl();
  }

  function includesAny(row: SliceRow, key: FacetKey, selected: Set<string>): boolean {
    if (selected.size === 0) return true;
    return valuesFor(row, key).some((value) => selected.has(value));
  }

  function haystack(row: SliceRow): string {
    return [
      row.id,
      row.title,
      row.description,
      row.family_id,
      row.family_name,
      row.protocol_id,
      row.protocol_name,
      row.dataset_id,
      row.dataset_name,
      row.status_label,
      row.comparison.species,
      row.comparison.modality,
      row.comparison.evidence_type,
      row.comparison.choice_type,
      row.comparison.response_modality,
      row.comparison.source_data_level,
      row.comparison.stimulus_metric,
      row.comparison.canonical_axis,
      row.comparison.analysis_outputs,
      row.comparison.data_scope,
      ...(row.metrics ?? []).map((metric) => `${metric.label} ${metric.value ?? ""}`),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
  }

  function matchesQuery(row: SliceRow, q: string): boolean {
    const tokens = q
      .toLowerCase()
      .split(/\s+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0);
    if (tokens.length === 0) return true;
    const text = haystack(row);
    return tokens.every((token) => text.includes(token));
  }

  function rowMatches(row: SliceRow): boolean {
    if (!matchesQuery(row, query.trim())) return false;
    if (!includesAny(row, "family", activeFamily)) return false;
    if (!includesAny(row, "species", activeSpecies)) return false;
    if (!includesAny(row, "modality", activeModality)) return false;
    if (!includesAny(row, "evidence", activeEvidence)) return false;
    if (!includesAny(row, "source", activeSource)) return false;
    if (statusMode === "available" && row.report_status !== "available") return false;
    if (statusMode === "missing" && row.report_status === "available") return false;
    return true;
  }

  function sorted(rowsToSort: SliceRow[]): SliceRow[] {
    return rowsToSort.slice().sort((a, b) => {
      if (sortMode === "trials-desc") {
        return trialCount(b) - trialCount(a) || a.title.localeCompare(b.title);
      }
      if (sortMode === "findings-desc") {
        return outputCount(b) - outputCount(a) || a.title.localeCompare(b.title);
      }
      if (sortMode === "report-first") {
        return (
          Number(b.report_status === "available") -
            Number(a.report_status === "available") ||
          a.title.localeCompare(b.title)
        );
      }
      if (sortMode === "family-asc") {
        return (
          (a.family_name ?? a.family_id).localeCompare(b.family_name ?? b.family_id) ||
          a.title.localeCompare(b.title)
        );
      }
      return a.title.localeCompare(b.title);
    });
  }

  const filteredRows = $derived(sorted(rows.filter(rowMatches)));

  const summary = $derived.by(() => {
    const families = new Set<string>();
    const protocols = new Set<string>();
    const datasets = new Set<string>();
    let reports = 0;
    let trials = 0;
    for (const row of filteredRows) {
      families.add(row.family_id);
      protocols.add(row.protocol_id);
      datasets.add(row.dataset_id);
      if (row.report_status === "available") reports += 1;
      trials += trialCount(row);
    }
    return { families: families.size, protocols: protocols.size, datasets: datasets.size, reports, trials };
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
          placeholder="slice, protocol, dataset, axis, metric"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
        />
      </label>
      <label class="text-xs text-slate-600">
        <span class="mb-1 block font-semibold text-slate-700">Report state</span>
        <select
          value={statusMode}
          onchange={updateStatus}
          class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
        >
          {#each Object.entries(statusLabels) as [value, label] (value)}
            <option value={value}>{label}</option>
          {/each}
        </select>
      </label>
      <label class="text-xs text-slate-600">
        <span class="mb-1 block font-semibold text-slate-700">Sort</span>
        <select
          value={sortMode}
          onchange={updateSort}
          class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm"
        >
          {#each Object.entries(sortLabels) as [value, label] (value)}
            <option value={value}>{label}</option>
          {/each}
        </select>
      </label>
    </div>

    <div class="mt-3 flex flex-wrap gap-2 text-xs">
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("reports")}>
        reports available
      </button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("visual")}>
        visual
      </button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("auditory")}>
        auditory
      </button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("processed")}>
        processed trials
      </button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("mouse")}>
        mouse
      </button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("missing")}>
        missing reports
      </button>
      {#if activeFilterCount > 0}
        <button type="button" class="rounded border border-slate-300 bg-slate-50 px-2 py-1 font-semibold text-slate-800 hover:border-accent hover:text-accent" onclick={clearAll}>
          clear {activeFilterCount}
        </button>
      {/if}
    </div>

    <div class="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-5">
      {#each Object.entries(options) as [key, facetOptions] (key)}
        <div class="min-w-0">
          <div class="mb-1 flex items-center justify-between gap-2 text-xs">
            <h2 class="font-semibold text-slate-700">
              {key === "family" ? "Family" : key === "species" ? "Species" : key === "modality" ? "Modality" : key === "evidence" ? "Evidence" : "Source"}
            </h2>
            {#if selectedSet(key as FacetKey).size > 0}
              <button type="button" class="text-slate-500 hover:text-accent" onclick={() => clearFacet(key as FacetKey)}>
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
      of <span class="font-mono text-slate-900">{rows.length}</span> slices ·
      <span class="font-mono text-slate-900">{summary.reports}</span> reports ·
      <span class="font-mono text-slate-900">{fmt(summary.trials)}</span> trials
    </p>
    <p class="text-xs text-slate-500">
      {summary.families} families · {summary.protocols} protocols · {summary.datasets} datasets
    </p>
  </div>

  {#if filteredRows.length === 0}
    <section class="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600">
      <p>No slices match the current filters.</p>
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
                <a class="text-slate-900 no-underline hover:text-accent" href={`/slices/${slugForId(row.id)}`}>
                  {row.title}
                </a>
              </h2>
              <p class="mt-1 break-all font-mono text-xs text-slate-500">{row.id}</p>
            </div>
            <span
              class={[
                "shrink-0 rounded px-2 py-0.5 text-xs",
                row.report_status === "available" ? "bg-ok-soft text-ok" : "bg-warn-soft text-warn",
              ]}
            >
              {row.report_status === "available" ? "report" : "missing"}
            </span>
          </header>

          {#if row.description}
            <p class="mt-3 text-sm text-slate-600">{row.description}</p>
          {/if}

          <div class="mt-3 flex flex-wrap gap-1 text-[11px]">
            <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{row.family_name ?? readable(row.family_id)}</span>
            <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{readable(row.comparison.species)}</span>
            <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{readable(row.comparison.modality)}</span>
            <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{readable(row.comparison.source_data_level)}</span>
          </div>

          <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs text-slate-700">
            <div>
              <dt class="text-slate-500">Evidence</dt>
              <dd>{readable(row.comparison.evidence_type)}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Choice</dt>
              <dd>{readable(row.comparison.choice_type)}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Axis</dt>
              <dd>{row.comparison.canonical_axis ?? row.comparison.stimulus_metric ?? "-"}</dd>
            </div>
            <div>
              <dt class="text-slate-500">Outputs</dt>
              <dd>{row.comparison.analysis_outputs ?? "-"}</dd>
            </div>
          </dl>

          {#if row.metrics && row.metrics.length > 0}
            <ul class="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs">
              {#each row.metrics.slice(0, 5) as metric (`${row.id}-${metric.label}`)}
                <li class="rounded bg-slate-100 px-2 py-0.5">
                  <span class="text-slate-500">{metric.label}</span>
                  <span class="ml-1 font-mono font-semibold text-slate-900">
                    {typeof metric.value === "number" ? metric.value.toLocaleString() : (metric.value ?? "-")}
                  </span>
                </li>
              {/each}
            </ul>
          {/if}

          <div class="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-4 text-xs">
            <a class="font-semibold text-accent" href={`/slices/${slugForId(row.id)}`}>Details</a>
            <a class="text-accent" href={`/protocols/${slugForId(row.protocol_id)}`}>{row.protocol_name ?? "Protocol"}</a>
            <a class="text-accent" href={`/datasets/${slugForId(row.dataset_id)}`}>{row.dataset_name ?? "Dataset"}</a>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
