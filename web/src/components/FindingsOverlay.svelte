<script lang="ts">
  import type { FindingsIndex, FindingsEntry } from "../lib/findings";

  let { data }: { data: FindingsIndex } = $props();

  type FilterKey = "species" | "source_data_level" | "evidence_type" | "response_modality";

  function uniqueOf(rows: FindingsEntry[], get: (e: FindingsEntry) => string | null | undefined): string[] {
    const out = new Set<string>();
    for (const r of rows) {
      const v = get(r);
      if (v !== null && v !== undefined && v !== "") out.add(v);
    }
    return Array.from(out).sort();
  }

  const allEntries: FindingsEntry[] = data.findings;
  const allCurveTypes = uniqueOf(allEntries, (e) => e.curve_type);
  const allYears = allEntries.map((e) => e.paper_year).filter((y): y is number => y != null);
  const minYear = allYears.length > 0 ? Math.min(...allYears) : 1990;
  const maxYear = allYears.length > 0 ? Math.max(...allYears) : new Date().getFullYear();

  const filterOptions = {
    species: uniqueOf(allEntries, (e) => e.species),
    source_data_level: uniqueOf(allEntries, (e) => e.source_data_level),
    evidence_type: uniqueOf(allEntries, (e) => e.evidence_type),
    response_modality: uniqueOf(allEntries, (e) => e.response_modality),
  } as const;

  const filterLabels: Record<FilterKey, string> = {
    species: "Species",
    source_data_level: "Source data level",
    evidence_type: "Evidence type",
    response_modality: "Response modality",
  };

  let currentCurveType = $state(
    allCurveTypes.includes("psychometric") ? "psychometric" : allCurveTypes[0] ?? "psychometric",
  );
  let active = $state<Record<FilterKey, Set<string>>>({
    species: new Set(filterOptions.species),
    source_data_level: new Set(filterOptions.source_data_level),
    evidence_type: new Set(filterOptions.evidence_type),
    response_modality: new Set(filterOptions.response_modality),
  });
  let yearStart = $state(minYear);
  let yearEnd = $state(maxYear);
  let searchText = $state("");

  const filteredEntries = $derived.by(() => {
    const needle = searchText.trim().toLowerCase();
    return allEntries.filter((entry) => {
      if (entry.curve_type !== currentCurveType) return false;
      const matches = (key: FilterKey, value: string | null | undefined): boolean => {
        if (value === null || value === undefined || value === "") return true;
        return active[key].has(value);
      };
      if (!matches("species", entry.species)) return false;
      if (!matches("source_data_level", entry.source_data_level)) return false;
      if (!matches("evidence_type", entry.evidence_type)) return false;
      if (!matches("response_modality", entry.response_modality)) return false;
      if (entry.paper_year < yearStart || entry.paper_year > yearEnd) return false;
      if (needle) {
        const haystack = [
          entry.paper_citation,
          entry.protocol_name,
          entry.family_name ?? "",
          entry.finding_id,
        ]
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      return true;
    });
  });

  const flatPoints = $derived.by(() =>
    filteredEntries.flatMap((entry) =>
      entry.points.map((p) => ({
        finding_id: entry.finding_id,
        paper_citation: entry.paper_citation,
        paper_year: entry.paper_year,
        species: entry.species ?? "unknown",
        source_data_level: entry.source_data_level,
        evidence_type: entry.evidence_type ?? "unknown",
        response_modality: entry.response_modality ?? "unknown",
        protocol_name: entry.protocol_name,
        x: p.x,
        y: p.y,
        n: p.n,
      }))
    )
  );

  const yLabel = $derived.by(() => {
    if (filteredEntries.length === 0) return "Y";
    return filteredEntries[0].y_label;
  });

  const yScale = $derived.by(() => {
    if (currentCurveType === "psychometric") return [0, 1] as [number, number];
    if (currentCurveType === "accuracy_by_strength") return [0, 1] as [number, number];
    return undefined;
  });

  function toggle(key: FilterKey, value: string) {
    const next = new Set(active[key]);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    active = { ...active, [key]: next };
  }

  function selectAll(key: FilterKey) {
    active = { ...active, [key]: new Set(filterOptions[key]) };
  }

  function selectNone(key: FilterKey) {
    active = { ...active, [key]: new Set() };
  }

  function resetFilters() {
    active = {
      species: new Set(filterOptions.species),
      source_data_level: new Set(filterOptions.source_data_level),
      evidence_type: new Set(filterOptions.evidence_type),
      response_modality: new Set(filterOptions.response_modality),
    };
    yearStart = minYear;
    yearEnd = maxYear;
    searchText = "";
  }

  let chartContainer: HTMLDivElement | undefined = $state();
  let chartReady = $state(false);
  let vegaEmbed: any = null;
  let chartView: any = null;

  $effect(() => {
    if (!chartContainer || vegaEmbed) return;
    (async () => {
      const mod = await import("vega-embed");
      vegaEmbed = mod.default ?? mod;
      chartReady = true;
    })();
  });

  $effect(() => {
    if (!chartContainer || !chartReady || !vegaEmbed) return;
    const points = flatPoints;
    const ySpec: Record<string, unknown> = {
      field: "y",
      type: "quantitative",
      title: yLabel,
    };
    if (yScale) {
      ySpec.scale = { domain: yScale };
    }
    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height: 380,
      data: { values: points },
      transform: [{ filter: "isValid(datum.x) && isValid(datum.y)" }],
      mark: { type: "line", point: true, interpolate: "linear" as const },
      encoding: {
        x: {
          field: "x",
          type: "quantitative" as const,
          title: filteredEntries[0]?.x_label ?? "x",
        },
        y: ySpec,
        color: {
          field: "paper_citation",
          type: "nominal" as const,
          title: "Paper",
          scale: { scheme: "tableau10" },
        },
        shape: {
          field: "source_data_level",
          type: "nominal" as const,
          title: "Source level",
        },
        detail: { field: "finding_id", type: "nominal" as const },
        tooltip: [
          { field: "paper_citation", title: "Paper" },
          { field: "paper_year", title: "Year" },
          { field: "species", title: "Species" },
          { field: "protocol_name", title: "Protocol" },
          { field: "source_data_level", title: "Source level" },
          { field: "x", title: "x", format: ".3f" },
          { field: "y", title: yLabel, format: ".3f" },
          { field: "n", title: "n" },
        ],
      },
      config: {
        view: { stroke: "#cbd5e1" },
        axis: { gridColor: "#e2e8f0", labelColor: "#334155" },
        legend: { labelColor: "#334155", titleColor: "#0f172a" },
      },
    };
    (async () => {
      try {
        const result = await vegaEmbed(chartContainer, spec, {
          actions: false,
          renderer: "svg",
        });
        chartView?.finalize?.();
        chartView = result.view;
      } catch (err) {
        console.error("vega-embed failed", err);
      }
    })();
  });
</script>

<div class="rounded-md border border-slate-200 bg-white p-4">
  <div class="mb-4 flex flex-wrap items-center gap-2">
    <span class="text-xs font-semibold text-slate-700">Curve type:</span>
    {#each allCurveTypes as type (type)}
      <button
        type="button"
        class:list={[
          "rounded-md border px-2.5 py-1 text-xs",
          type === currentCurveType
            ? "border-accent bg-accent text-white"
            : "border-slate-300 text-slate-700 hover:bg-slate-50",
        ]}
        onclick={() => (currentCurveType = type)}
      >
        {type.replace(/_/g, " ")}
      </button>
    {/each}
    <button
      type="button"
      class="ml-auto rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50"
      onclick={resetFilters}
    >
      Reset filters
    </button>
  </div>

  <div class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
    {#each Object.entries(filterOptions) as [key, values] (key)}
      <fieldset class="rounded border border-slate-200 p-3">
        <legend class="px-1 text-xs font-semibold text-slate-700">
          {filterLabels[key as FilterKey]}
        </legend>
        <div class="mt-1 flex flex-wrap gap-x-4 gap-y-1">
          {#each values as value (value)}
            <label class="flex items-center gap-1 text-xs text-slate-700">
              <input
                type="checkbox"
                checked={active[key as FilterKey].has(value)}
                onchange={() => toggle(key as FilterKey, value)}
              />
              {value}
            </label>
          {/each}
        </div>
        <div class="mt-2 flex gap-2 text-[11px]">
          <button
            type="button"
            class="text-accent underline"
            onclick={() => selectAll(key as FilterKey)}
          >
            All
          </button>
          <button
            type="button"
            class="text-accent underline"
            onclick={() => selectNone(key as FilterKey)}
          >
            None
          </button>
        </div>
      </fieldset>
    {/each}
  </div>

  <div class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
    <fieldset class="rounded border border-slate-200 p-3">
      <legend class="px-1 text-xs font-semibold text-slate-700">Year range</legend>
      <div class="mt-1 flex items-center gap-2 text-xs text-slate-700">
        <input
          type="number"
          min={minYear}
          max={maxYear}
          bind:value={yearStart}
          class="w-20 rounded border border-slate-200 px-1 py-0.5"
        />
        <span>–</span>
        <input
          type="number"
          min={minYear}
          max={maxYear}
          bind:value={yearEnd}
          class="w-20 rounded border border-slate-200 px-1 py-0.5"
        />
        <span class="ml-2 text-[11px] text-slate-500">
          (atlas: {minYear}–{maxYear})
        </span>
      </div>
    </fieldset>
    <fieldset class="rounded border border-slate-200 p-3">
      <legend class="px-1 text-xs font-semibold text-slate-700">Search</legend>
      <input
        type="search"
        placeholder="paper / protocol / finding id…"
        bind:value={searchText}
        class="mt-1 w-full rounded border border-slate-200 px-2 py-1 text-xs"
      />
    </fieldset>
  </div>

  <p class="mb-2 text-xs text-slate-600">
    Showing {filteredEntries.length} of {allEntries.length} findings,
    {flatPoints.length} points.
  </p>

  <div bind:this={chartContainer} class="w-full"></div>

  <p class="mt-3 text-[11px] text-slate-500">
    Curves at different source-data levels are shown on shared axes for visual
    comparison; point shape encodes the source level. Values for figure-source-
    data findings should be read as published rather than as a complete raw
    behavioral export.
  </p>
</div>
