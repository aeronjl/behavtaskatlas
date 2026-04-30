<script lang="ts">
  import FacetBar from "./FacetBar.svelte";

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

  type Option = { value: string; label: string; count: number };

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
  let selected = $state<Record<string, Set<string>>>({
    family: initialSet("family"),
    species: initialSet("species"),
    modality: initialSet("modality"),
    evidence: initialSet("evidence"),
    source: initialSet("source"),
  });

  const facets = $derived([
    { key: "family", label: "Family", options: options.family },
    { key: "species", label: "Species", options: options.species },
    { key: "modality", label: "Modality", options: options.modality },
    { key: "evidence", label: "Evidence", options: options.evidence },
    { key: "source", label: "Source", options: options.source },
  ]);

  const sortOptions = Object.entries(sortLabels).map(([value, label]) => ({
    value,
    label,
  }));
  const stateOptions = Object.entries(statusLabels).map(([value, label]) => ({
    value,
    label,
  }));

  const presets = [
    { key: "reports", label: "reports available" },
    { key: "visual", label: "visual" },
    { key: "auditory", label: "auditory" },
    { key: "processed", label: "processed trials" },
    { key: "mouse", label: "mouse" },
    { key: "missing", label: "missing reports" },
  ];

  const activeFilterCount = $derived(
    (selected.family?.size ?? 0) +
      (selected.species?.size ?? 0) +
      (selected.modality?.size ?? 0) +
      (selected.evidence?.size ?? 0) +
      (selected.source?.size ?? 0) +
      (statusMode === "all" ? 0 : 1) +
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
    sortMode = "title-asc";
    statusMode = "all";
    selected = {
      family: new Set(),
      species: new Set(),
      modality: new Set(),
      evidence: new Set(),
      source: new Set(),
    };
  }

  function applyPreset(preset: string) {
    resetFilters();
    if (preset === "reports") statusMode = "available";
    if (preset === "missing") statusMode = "missing";
    if (preset === "visual") setFacetValues("modality", ["visual"]);
    if (preset === "auditory") setFacetValues("modality", ["auditory"]);
    if (preset === "processed") setFacetValues("source", ["processed-trial"]);
    if (preset === "mouse") setFacetValues("species", ["mouse"]);
  }

  // URL sync — runs whenever filter state changes; replaceState skips
  // adding history entries for filter tweaks.
  $effect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    if (query.trim().length > 0) params.set("q", query.trim());
    if (sortMode !== "title-asc") params.set("sort", sortMode);
    if (statusMode !== "all") params.set("report", statusMode);
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

  function includesAny(row: SliceRow, key: FacetKey, set: Set<string>): boolean {
    if (set.size === 0) return true;
    return valuesFor(row, key).some((value) => set.has(value));
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
    if (!includesAny(row, "family", selected.family ?? new Set())) return false;
    if (!includesAny(row, "species", selected.species ?? new Set())) return false;
    if (!includesAny(row, "modality", selected.modality ?? new Set())) return false;
    if (!includesAny(row, "evidence", selected.evidence ?? new Set())) return false;
    if (!includesAny(row, "source", selected.source ?? new Set())) return false;
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
    return {
      families: families.size,
      protocols: protocols.size,
      datasets: datasets.size,
      reports,
      trials,
    };
  });
</script>

<section class="space-y-4">
  <FacetBar
    searchPlaceholder="slice, protocol, dataset, axis, metric"
    bind:query
    {sortOptions}
    bind:sortMode
    sortLabel="Sort"
    {stateOptions}
    bind:stateMode={statusMode}
    stateLabel="Report state"
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
      of <span class="font-mono text-fg">{rows.length}</span> slices ·
      <span class="font-mono text-fg">{summary.reports}</span> reports ·
      <span class="font-mono text-fg">{fmt(summary.trials)}</span> trials
    </p>
    <p class="text-body-xs text-fg-muted">
      {summary.families} families · {summary.protocols} protocols · {summary.datasets} datasets
    </p>
  </div>

  {#if filteredRows.length === 0}
    <section class="rounded-md border border-rule bg-surface-raised p-6 text-body text-fg-secondary">
      <p>No slices match the current filters.</p>
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
                <a class="text-fg no-underline hover:text-accent" href={`/slices/${slugForId(row.id)}`}>
                  {row.title}
                </a>
              </h2>
              <p class="mt-1 break-all font-mono text-mono-id text-fg-muted">{row.id}</p>
            </div>
            <span
              class={[
                "shrink-0 rounded px-2 py-0.5 text-body-xs",
                row.report_status === "available" ? "bg-ok-soft text-ok" : "bg-warn-soft text-warn",
              ]}
            >
              {row.report_status === "available" ? "report" : "missing"}
            </span>
          </header>

          {#if row.description}
            <p class="mt-3 text-body text-fg-secondary">{row.description}</p>
          {/if}

          <div class="mt-3 flex flex-wrap gap-1 text-mono-id">
            <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">{row.family_name ?? readable(row.family_id)}</span>
            <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">{readable(row.comparison.species)}</span>
            <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">{readable(row.comparison.modality)}</span>
            <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">{readable(row.comparison.source_data_level)}</span>
          </div>

          <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-body-xs text-fg-secondary">
            <div>
              <dt class="text-fg-muted">Evidence</dt>
              <dd>{readable(row.comparison.evidence_type)}</dd>
            </div>
            <div>
              <dt class="text-fg-muted">Choice</dt>
              <dd>{readable(row.comparison.choice_type)}</dd>
            </div>
            <div>
              <dt class="text-fg-muted">Axis</dt>
              <dd>{row.comparison.canonical_axis ?? row.comparison.stimulus_metric ?? "-"}</dd>
            </div>
            <div>
              <dt class="text-fg-muted">Outputs</dt>
              <dd>{row.comparison.analysis_outputs ?? "-"}</dd>
            </div>
          </dl>

          {#if row.metrics && row.metrics.length > 0}
            <ul class="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-body-xs">
              {#each row.metrics.slice(0, 5) as metric (`${row.id}-${metric.label}`)}
                <li class="rounded bg-surface-sunken px-2 py-0.5">
                  <span class="text-fg-muted">{metric.label}</span>
                  <span class="ml-1 font-mono font-semibold text-fg">
                    {typeof metric.value === "number" ? metric.value.toLocaleString() : (metric.value ?? "-")}
                  </span>
                </li>
              {/each}
            </ul>
          {/if}

          <div class="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-4 text-body-xs">
            <a class="font-semibold text-accent" href={`/slices/${slugForId(row.id)}`}>Details</a>
            <a class="text-accent" href={`/protocols/${slugForId(row.protocol_id)}`}>{row.protocol_name ?? "Protocol"}</a>
            <a class="text-accent" href={`/datasets/${slugForId(row.dataset_id)}`}>{row.dataset_name ?? "Dataset"}</a>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</section>
