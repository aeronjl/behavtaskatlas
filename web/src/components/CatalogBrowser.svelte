<script lang="ts">
  import FacetBar from "./FacetBar.svelte";

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

  const facets = $derived([
    {
      key: "species",
      label: "Species",
      mode: "single" as const,
      allLabel: "All species",
      options: speciesOptions,
    },
    {
      key: "modality",
      label: "Modality",
      mode: "single" as const,
      allLabel: "All modalities",
      options: modalityOptions,
    },
    {
      key: "source",
      label: "Source",
      mode: "single" as const,
      allLabel: "All sources",
      options: sourceOptions,
    },
    {
      key: "status",
      label: "Status",
      mode: "single" as const,
      allLabel: "All statuses",
      options: statusOptions,
    },
  ]);

  const sortOptions = Object.entries(sortLabels).map(([value, label]) => ({
    value,
    label,
  }));

  function initialParam(name: string): string | null {
    if (typeof window === "undefined") return null;
    return new URLSearchParams(window.location.search).get(name);
  }

  function initialTypeSet(): Set<CatalogRow["record_type"]> {
    const raw = initialParam("type");
    if (!raw) return new Set(allTypes);
    const requested = raw
      .split(",")
      .map((value) => value.trim())
      .filter((value): value is CatalogRow["record_type"] =>
        allTypes.includes(value as CatalogRow["record_type"]),
      );
    return requested.length > 0 ? new Set(requested) : new Set(allTypes);
  }

  function initialSingle(name: string): Set<string> {
    const value = initialParam(name);
    return value && value !== "all" ? new Set([value]) : new Set<string>();
  }

  const initialSort = initialParam("sort") ?? "type";

  let query = $state(initialParam("q") ?? "");
  let sortMode = $state(sortLabels[initialSort] ? initialSort : "type");
  let activeTypes = $state(initialTypeSet());
  let selected = $state<Record<string, Set<string>>>({
    species: initialSingle("species"),
    modality: initialSingle("modality"),
    source: initialSingle("source"),
    status: initialSingle("status"),
  });

  const activeFilterCount = $derived(
    (query.trim().length > 0 ? 1 : 0) +
      (activeTypes.size === allTypes.length ? 0 : 1) +
      ((selected.species?.size ?? 0) > 0 ? 1 : 0) +
      ((selected.modality?.size ?? 0) > 0 ? 1 : 0) +
      ((selected.source?.size ?? 0) > 0 ? 1 : 0) +
      ((selected.status?.size ?? 0) > 0 ? 1 : 0),
  );

  function toggleType(type: CatalogRow["record_type"]) {
    const next = new Set(activeTypes);
    if (next.has(type)) next.delete(type);
    else next.add(type);
    if (next.size === 0) allTypes.forEach((value) => next.add(value));
    activeTypes = next;
  }

  function clearAll() {
    query = "";
    activeTypes = new Set(allTypes);
    sortMode = "type";
    selected = {
      species: new Set(),
      modality: new Set(),
      source: new Set(),
      status: new Set(),
    };
  }

  $effect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    if (query.trim().length > 0) params.set("q", query.trim());
    if (activeTypes.size !== allTypes.length) {
      params.set("type", allTypes.filter((type) => activeTypes.has(type)).join(","));
    }
    const single = (key: string) => Array.from(selected[key] ?? new Set())[0];
    if (single("species")) params.set("species", single("species")!);
    if (single("modality")) params.set("modality", single("modality")!);
    if (single("source")) params.set("source", single("source")!);
    if (single("status")) params.set("status", single("status")!);
    if (sortMode !== "type") params.set("sort", sortMode);
    const search = params.toString();
    const next = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(null, "", next);
    }
  });

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
    const speciesPick = Array.from(selected.species ?? new Set())[0];
    const modalityPick = Array.from(selected.modality ?? new Set())[0];
    const sourcePick = Array.from(selected.source ?? new Set())[0];
    const statusPick = Array.from(selected.status ?? new Set())[0];
    if (speciesPick && !(row.species ?? []).includes(speciesPick)) return false;
    if (modalityPick && !(row.modalities ?? []).includes(modalityPick)) return false;
    if (sourcePick && row.source_data_level !== sourcePick) return false;
    if (statusPick && row.status !== statusPick) return false;
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

<section class="space-y-4">
  <FacetBar
    searchPlaceholder="family, protocol, dataset, slice"
    bind:query
    {sortOptions}
    bind:sortMode
    sortLabel="Sort"
    {facets}
    bind:selected
    {activeFilterCount}
    onClearAll={clearAll}
  />

  <div class="flex flex-wrap items-center gap-2 text-body-xs text-fg-secondary">
    <span class="text-fg-muted">Types:</span>
    {#each allTypes as type (type)}
      {@const active = activeTypes.has(type)}
      <button
        type="button"
        class={[
          "rounded border px-2 py-0.5",
          active
            ? "border-accent bg-accent text-white"
            : "border-rule-strong bg-surface-raised text-fg-secondary hover:border-rule-emphasis hover:text-accent",
        ]}
        onclick={() => toggleType(type)}
      >
        {typeLabels[type]} · {typeCounts.get(type) ?? 0}
      </button>
    {/each}
  </div>

  <p class="text-body text-fg-secondary">
    Showing <span class="font-mono font-semibold text-fg">{filteredRows.length}</span>
    of <span class="font-mono text-fg">{rows.length}</span> records ·
    <span class="font-mono text-fg">{summary.get("family") ?? 0}</span> families ·
    <span class="font-mono text-fg">{summary.get("protocol") ?? 0}</span> protocols ·
    <span class="font-mono text-fg">{summary.get("dataset") ?? 0}</span> datasets ·
    <span class="font-mono text-fg">{summary.get("slice") ?? 0}</span> slices
  </p>

  {#if filteredRows.length === 0}
    <section class="rounded-md border border-rule bg-surface p-4 text-body text-fg-secondary">
      <p>No catalog records match the current filters.</p>
      {#if activeFilterCount > 0}
        <button
          type="button"
          class="mt-3 block rounded border border-rule-strong bg-surface-raised px-2 py-1 text-body-xs font-semibold text-fg hover:border-rule-emphasis hover:text-accent"
          onclick={clearAll}
        >
          Clear filters
        </button>
      {/if}
    </section>
  {:else}
    <ul class="mt-4 divide-y divide-rule rounded-md border border-rule bg-surface-raised">
      {#each visibleRows as row (row.id)}
        <li class="px-3 py-2 text-body">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between">
            <div class="min-w-0">
              <a class="font-medium text-fg no-underline hover:text-accent" href={row.href}>
                {row.title}
              </a>
              <p class="mt-0.5 break-all font-mono text-mono-id text-fg-muted">{row.id}</p>
            </div>
            <span class="w-fit rounded bg-surface-sunken px-1.5 py-0.5 text-mono-id uppercase tracking-wide text-fg-muted">
              {typeLabels[row.record_type]}
            </span>
          </div>
          <p class="mt-1 text-body-xs text-fg-secondary">
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
            <p class="mt-1 line-clamp-2 text-body-xs text-fg-muted">{row.body}</p>
          {/if}
        </li>
      {/each}
    </ul>
    {#if filteredRows.length > 80}
      <p class="mt-2 text-body-xs text-fg-muted">Showing first 80 matching records.</p>
    {/if}
  {/if}
</section>
