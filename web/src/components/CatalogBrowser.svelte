<script lang="ts">
  type CatalogRow = {
    body?: string | null;
    choice_type?: string | null;
    dataset_count?: number | null;
    evidence_type?: string | null;
    family_id?: string | null;
    family_name?: string | null;
    href: string;
    id: string;
    modalities?: string[] | null;
    protocol_count?: number | null;
    record_type: "family" | "protocol" | "dataset" | "slice";
    slice_count?: number | null;
    source_data_level?: string | null;
    species?: string[] | null;
    status?: string | null;
    title: string;
  };

  type Option = {
    value: string;
    label: string;
    count: number;
  };

  let { rows }: { rows: CatalogRow[] } = $props();

  const typeLabels: Record<CatalogRow["record_type"], string> = {
    family: "Family",
    protocol: "Protocol",
    dataset: "Dataset",
    slice: "Slice",
  };

  const allTypes = Object.keys(typeLabels) as CatalogRow["record_type"][];
  const sortLabels: Record<string, string> = {
    type: "Type, then title",
    title: "Title A-Z",
    coverage: "Most covered",
  };

  function initialParam(name: string): string | null {
    if (typeof window === "undefined") return null;
    return new URLSearchParams(window.location.search).get(name);
  }

  function readable(value: string | null | undefined): string {
    if (!value) return "-";
    if (value === "non-human-primate") return "NHP";
    if (value === "processed-trial") return "processed trials";
    if (value === "raw-trial") return "raw trials";
    if (value === "figure-source-data") return "figure source data";
    return value.replace(/[_-]/g, " ");
  }

  function countOptions(values: string[]): Option[] {
    const counts = new Map<string, number>();
    for (const value of values.filter(Boolean)) {
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
    return Array.from(counts.entries())
      .map(([value, count]) => ({ value, label: readable(value), count }))
      .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  }

  const typeCounts = $derived.by(() => {
    const counts = new Map<CatalogRow["record_type"], number>();
    for (const row of rows) {
      counts.set(row.record_type, (counts.get(row.record_type) ?? 0) + 1);
    }
    return counts;
  });

  const speciesOptions = $derived(countOptions(rows.flatMap((row) => row.species ?? [])));
  const modalityOptions = $derived(countOptions(rows.flatMap((row) => row.modalities ?? [])));
  const sourceOptions = $derived(
    countOptions(rows.map((row) => row.source_data_level ?? "").filter(Boolean)),
  );
  const statusOptions = $derived(
    countOptions(rows.map((row) => row.status ?? "").filter(Boolean)),
  );

  function initialTypeSet(): Set<CatalogRow["record_type"]> {
    const raw = initialParam("type");
    if (!raw) return new Set(allTypes);
    const selected = raw
      .split(",")
      .map((value) => value.trim())
      .filter((value): value is CatalogRow["record_type"] =>
        allTypes.includes(value as CatalogRow["record_type"]),
      );
    return selected.length > 0 ? new Set(selected) : new Set(allTypes);
  }

  function initialOption(name: string): string {
    return initialParam(name) ?? "all";
  }

  const initialSort = initialParam("sort") ?? "type";

  let query = $state(initialParam("q") ?? "");
  let activeTypes = $state(initialTypeSet());
  let species = $state(initialOption("species"));
  let modality = $state(initialOption("modality"));
  let sourceLevel = $state(initialOption("source"));
  let status = $state(initialOption("status"));
  let sortMode = $state(sortLabels[initialSort] ? initialSort : "type");

  const activeFilterCount = $derived(
    (query.trim().length > 0 ? 1 : 0) +
      (activeTypes.size === allTypes.length ? 0 : 1) +
      (species === "all" ? 0 : 1) +
      (modality === "all" ? 0 : 1) +
      (sourceLevel === "all" ? 0 : 1) +
      (status === "all" ? 0 : 1),
  );

  function syncUrl() {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    if (query.trim().length > 0) params.set("q", query.trim());
    if (activeTypes.size !== allTypes.length) {
      params.set("type", allTypes.filter((type) => activeTypes.has(type)).join(","));
    }
    if (species !== "all") params.set("species", species);
    if (modality !== "all") params.set("modality", modality);
    if (sourceLevel !== "all") params.set("source", sourceLevel);
    if (status !== "all") params.set("status", status);
    if (sortMode !== "type") params.set("sort", sortMode);
    const search = params.toString();
    const next = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(null, "", next);
    }
  }

  function toggleType(type: CatalogRow["record_type"]) {
    const next = new Set(activeTypes);
    if (next.has(type)) next.delete(type);
    else next.add(type);
    if (next.size === 0) allTypes.forEach((value) => next.add(value));
    activeTypes = next;
    syncUrl();
  }

  function clearAll() {
    query = "";
    activeTypes = new Set(allTypes);
    species = "all";
    modality = "all";
    sourceLevel = "all";
    status = "all";
    sortMode = "type";
    syncUrl();
  }

  function updateQuery(event: Event) {
    query = (event.currentTarget as HTMLInputElement).value;
    syncUrl();
  }

  function updateSelect(event: Event, field: string) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    if (field === "species") species = value;
    if (field === "modality") modality = value;
    if (field === "source") sourceLevel = value;
    if (field === "status") status = value;
    if (field === "sort") sortMode = value;
    syncUrl();
  }

  function haystack(row: CatalogRow): string {
    return [
      row.id,
      row.title,
      row.body,
      row.family_id,
      row.family_name,
      row.choice_type,
      row.evidence_type,
      row.source_data_level,
      row.status,
      ...(row.species ?? []),
      ...(row.modalities ?? []),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
  }

  function matchesQuery(row: CatalogRow): boolean {
    const tokens = query
      .toLowerCase()
      .split(/\s+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0);
    if (tokens.length === 0) return true;
    const text = haystack(row);
    return tokens.every((token) => text.includes(token));
  }

  function rowMatches(row: CatalogRow): boolean {
    if (!activeTypes.has(row.record_type)) return false;
    if (!matchesQuery(row)) return false;
    if (species !== "all" && !(row.species ?? []).includes(species)) return false;
    if (modality !== "all" && !(row.modalities ?? []).includes(modality)) return false;
    if (sourceLevel !== "all" && row.source_data_level !== sourceLevel) return false;
    if (status !== "all" && row.status !== status) return false;
    return true;
  }

  function sorted(rowsToSort: CatalogRow[]): CatalogRow[] {
    return rowsToSort.slice().sort((a, b) => {
      if (sortMode === "title") return a.title.localeCompare(b.title);
      if (sortMode === "coverage") {
        return (
          (b.slice_count ?? 0) - (a.slice_count ?? 0) ||
          (b.dataset_count ?? 0) - (a.dataset_count ?? 0) ||
          a.title.localeCompare(b.title)
        );
      }
      return (
        allTypes.indexOf(a.record_type) - allTypes.indexOf(b.record_type) ||
        a.title.localeCompare(b.title)
      );
    });
  }

  const filteredRows = $derived(sorted(rows.filter(rowMatches)));
  const visibleRows = $derived(filteredRows.slice(0, 80));

  const summary = $derived.by(() => {
    const counts = new Map<CatalogRow["record_type"], number>();
    for (const row of filteredRows) {
      counts.set(row.record_type, (counts.get(row.record_type) ?? 0) + 1);
    }
    return counts;
  });
</script>

<section class="rounded-md border border-slate-200 bg-white p-4">
  <div class="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1.6fr)_repeat(5,minmax(9rem,0.8fr))]">
    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Search catalog</span>
      <input
        value={query}
        oninput={updateQuery}
        type="search"
        class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        placeholder="family, protocol, dataset, slice"
        autocomplete="off"
        autocapitalize="none"
        spellcheck="false"
      />
    </label>

    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Species</span>
      <select value={species} onchange={(event) => updateSelect(event, "species")} class="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm">
        <option value="all">All species</option>
        {#each speciesOptions as option (option.value)}
          <option value={option.value}>{option.label} · {option.count}</option>
        {/each}
      </select>
    </label>

    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Modality</span>
      <select value={modality} onchange={(event) => updateSelect(event, "modality")} class="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm">
        <option value="all">All modalities</option>
        {#each modalityOptions as option (option.value)}
          <option value={option.value}>{option.label} · {option.count}</option>
        {/each}
      </select>
    </label>

    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Source</span>
      <select value={sourceLevel} onchange={(event) => updateSelect(event, "source")} class="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm">
        <option value="all">All sources</option>
        {#each sourceOptions as option (option.value)}
          <option value={option.value}>{option.label} · {option.count}</option>
        {/each}
      </select>
    </label>

    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Status</span>
      <select value={status} onchange={(event) => updateSelect(event, "status")} class="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm">
        <option value="all">All statuses</option>
        {#each statusOptions as option (option.value)}
          <option value={option.value}>{option.label} · {option.count}</option>
        {/each}
      </select>
    </label>

    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Sort</span>
      <select value={sortMode} onchange={(event) => updateSelect(event, "sort")} class="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm">
        {#each Object.entries(sortLabels) as [value, label] (value)}
          <option value={value}>{label}</option>
        {/each}
      </select>
    </label>
  </div>

  <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
    <span class="text-slate-500">Types:</span>
    {#each allTypes as type (type)}
      {@const active = activeTypes.has(type)}
      <button
        type="button"
        class={[
          "rounded border px-2 py-0.5",
          active
            ? "border-accent bg-accent text-white"
            : "border-slate-300 bg-white text-slate-700 hover:border-accent hover:text-accent",
        ]}
        onclick={() => toggleType(type)}
      >
        {typeLabels[type]} · {typeCounts.get(type) ?? 0}
      </button>
    {/each}
    {#if activeFilterCount > 0}
      <button
        type="button"
        class="rounded border border-slate-300 bg-slate-50 px-2 py-0.5 font-semibold text-slate-800 hover:border-accent hover:text-accent"
        onclick={clearAll}
      >
        clear {activeFilterCount}
      </button>
    {/if}
  </div>

  <p class="mt-3 text-sm text-slate-600">
    Showing <span class="font-mono font-semibold text-slate-900">{filteredRows.length}</span>
    of <span class="font-mono text-slate-900">{rows.length}</span> records ·
    <span class="font-mono text-slate-900">{summary.get("family") ?? 0}</span> families ·
    <span class="font-mono text-slate-900">{summary.get("protocol") ?? 0}</span> protocols ·
    <span class="font-mono text-slate-900">{summary.get("dataset") ?? 0}</span> datasets ·
    <span class="font-mono text-slate-900">{summary.get("slice") ?? 0}</span> slices
  </p>

  {#if filteredRows.length === 0}
    <section class="mt-4 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
      <p>No catalog records match the current filters.</p>
      {#if activeFilterCount > 0}
        <button type="button" class="mt-3 block rounded border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-800 hover:border-accent hover:text-accent" onclick={clearAll}>
          Clear filters
        </button>
      {/if}
    </section>
  {:else}
    <ul class="mt-4 divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
      {#each visibleRows as row (row.id)}
        <li class="px-3 py-2 text-sm">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between">
            <div class="min-w-0">
              <a class="font-medium text-slate-900 no-underline hover:text-accent" href={row.href}>
                {row.title}
              </a>
              <p class="mt-0.5 break-all font-mono text-[11px] text-slate-500">{row.id}</p>
            </div>
            <span class="w-fit rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-500">
              {typeLabels[row.record_type]}
            </span>
          </div>
          <p class="mt-1 text-xs text-slate-600">
            {row.family_name ? `${row.family_name} · ` : ""}
            {[
              ...(row.species ?? []).map(readable),
              ...(row.modalities ?? []).map(readable),
              readable(row.evidence_type),
              readable(row.choice_type),
              readable(row.source_data_level),
            ].filter((value) => value !== "-").join(" · ")}
          </p>
          {#if row.body}
            <p class="mt-1 line-clamp-2 text-xs text-slate-500">{row.body}</p>
          {/if}
        </li>
      {/each}
    </ul>
    {#if filteredRows.length > 80}
      <p class="mt-2 text-xs text-slate-500">Showing first 80 matching records.</p>
    {/if}
  {/if}
</section>
