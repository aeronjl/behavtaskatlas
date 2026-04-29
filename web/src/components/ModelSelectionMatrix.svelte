<script lang="ts">
  type CaveatDefinition = {
    label: string;
    description: string;
  };

  type ConfidenceDefinition = {
    label: string;
    description: string;
  };

  type ScopeDefinition = {
    label: string;
    description: string;
  };

  type MatrixColumn = {
    id: string;
    label: string;
    description: string;
  };

  type MatrixCell = {
    fit_id: string;
    variant_id: string;
    variant_label: string;
    aic: number | null;
    delta_from_best: number | null;
    is_winner: boolean;
    caveat_tags: string[];
  };

  type MatrixRow = {
    selection_id: string;
    finding_id: string;
    finding_href: string;
    paper_label: string;
    paper_href: string;
    species: string;
    task_family: string;
    protocol_name: string;
    curve_type: string;
    source_data_level: string;
    source_status: string;
    confidence_label: string;
    comparison_scope: string;
    best_fit_id: string;
    best_variant_id: string;
    n_candidate_fits: number;
    candidate_comparison_scopes: string[];
    candidate_caveat_tags: string[];
    interpretation_warning?: {
      warning_type: string;
      severity: string;
      message: string;
    } | null;
    cells: Record<string, MatrixCell | null>;
  };

  let {
    rows,
    columns,
    caveatDefinitions = {},
    confidenceDefinitions = {},
    scopeDefinitions = {},
  }: {
    rows: MatrixRow[];
    columns: MatrixColumn[];
    caveatDefinitions?: Record<string, CaveatDefinition>;
    confidenceDefinitions?: Record<string, ConfidenceDefinition>;
    scopeDefinitions?: Record<string, ScopeDefinition>;
  } = $props();

  let query = $state("");
  let species = $state("all");
  let taskFamily = $state("all");
  let curveType = $state("all");
  let sourceStatus = $state("all");
  let confidence = $state("all");
  let scope = $state("all");
  let sortMode = $state("triage");

  const speciesOptions = $derived(
    Array.from(new Set(rows.map((row) => row.species).filter(Boolean))).sort(),
  );
  const familyOptions = $derived(
    Array.from(new Set(rows.map((row) => row.task_family).filter(Boolean))).sort(),
  );
  const curveOptions = $derived(
    Array.from(new Set(rows.map((row) => row.curve_type).filter(Boolean))).sort(),
  );
  const sourceOptions = $derived(
    Array.from(new Set(rows.map((row) => row.source_status).filter(Boolean))).sort(),
  );
  const confidenceOptions = $derived(
    Array.from(new Set(rows.map((row) => row.confidence_label).filter(Boolean))).sort(),
  );
  const scopeOptions = $derived(
    Array.from(new Set(rows.map((row) => row.comparison_scope).filter(Boolean))).sort(),
  );

  function labelForConfidence(label: string): string {
    return confidenceDefinitions[label]?.label ?? label.replace(/_/g, " ");
  }

  function labelForCaveat(tag: string): string {
    return caveatDefinitions[tag]?.label ?? tag.replace(/_/g, " ");
  }

  function labelForScope(value: string): string {
    return scopeDefinitions[value]?.label ?? value.replace(/_/g, " ");
  }

  function fmt(value: number | null | undefined, digits = 1): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return "-";
    return value.toFixed(digits);
  }

  function confidenceRank(label: string): number {
    if (label === "close") return 0;
    if (label === "single_candidate") return 1;
    if (label === "supported") return 2;
    if (label === "decisive") return 3;
    return 4;
  }

  function confidenceClass(label: string): string {
    if (label === "decisive") return "bg-ok-soft text-ok";
    if (label === "supported") return "bg-accent-soft text-accent";
    if (label === "close") return "bg-warn-soft text-warn";
    return "bg-slate-100 text-slate-600";
  }

  function sourceClass(status: string): string {
    if (status === "trial-backed") return "bg-ok-soft text-ok";
    if (status === "proxy-backed") return "bg-warn-soft text-warn";
    return "bg-slate-100 text-slate-600";
  }

  function scopeClass(value: string): string {
    if (value === "direct_choice") return "bg-ok-soft text-ok";
    if (value === "joint_choice_rt") return "bg-accent-soft text-accent";
    if (value === "chronometric_summary" || value === "accuracy_summary") {
      return "bg-warn-soft text-warn";
    }
    return "bg-slate-100 text-slate-600";
  }

  function cellClass(cell: MatrixCell | null): string {
    const base = "min-w-36 px-3 py-2 align-top";
    if (!cell) return `${base} bg-slate-50 text-slate-400`;
    if (cell.is_winner) return `${base} bg-ok-soft`;
    return `${base} bg-white`;
  }

  function haystack(row: MatrixRow): string {
    const cellText = columns
      .map((column) => row.cells[column.id])
      .filter(Boolean)
      .map((cell) => [
        cell?.fit_id,
        cell?.variant_id,
        cell?.variant_label,
        ...(cell?.caveat_tags ?? []),
      ].join(" "))
      .join(" ");
    return [
      row.selection_id,
      row.finding_id,
      row.paper_label,
      row.species,
      row.task_family,
      row.protocol_name,
      row.curve_type,
      row.source_data_level,
      row.source_status,
      row.confidence_label,
      row.comparison_scope,
      row.best_fit_id,
      row.best_variant_id,
      ...row.candidate_comparison_scopes,
      ...row.candidate_caveat_tags,
      row.interpretation_warning?.warning_type,
      row.interpretation_warning?.message,
      cellText,
    ]
      .join(" ")
      .toLowerCase();
  }

  const filteredRows = $derived.by(() => {
    const q = query.trim().toLowerCase();
    const out = rows.filter((row) => {
      if (q && !haystack(row).includes(q)) return false;
      if (species !== "all" && row.species !== species) return false;
      if (taskFamily !== "all" && row.task_family !== taskFamily) return false;
      if (curveType !== "all" && row.curve_type !== curveType) return false;
      if (sourceStatus !== "all" && row.source_status !== sourceStatus) return false;
      if (confidence !== "all" && row.confidence_label !== confidence) return false;
      if (scope !== "all" && row.comparison_scope !== scope) return false;
      return true;
    });
    return out.sort((a, b) => {
      if (sortMode === "finding") return a.finding_id.localeCompare(b.finding_id);
      if (sortMode === "candidates-desc") {
        return b.n_candidate_fits - a.n_candidate_fits;
      }
      if (sortMode === "confidence-strong") {
        return confidenceRank(b.confidence_label) - confidenceRank(a.confidence_label);
      }
      return (
        confidenceRank(a.confidence_label) - confidenceRank(b.confidence_label) ||
        b.n_candidate_fits - a.n_candidate_fits ||
        a.finding_id.localeCompare(b.finding_id)
      );
    });
  });
</script>

<div class="space-y-3">
  <div class="grid grid-cols-1 gap-2 lg:grid-cols-[1.4fr_repeat(7,minmax(0,1fr))]">
    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Search</span>
      <input
        bind:value={query}
        type="search"
        class="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        placeholder="finding, paper, model, caveat"
      />
    </label>
    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Species</span>
      <select bind:value={species} class="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm">
        <option value="all">All species</option>
        {#each speciesOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Family</span>
      <select bind:value={taskFamily} class="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm">
        <option value="all">All families</option>
        {#each familyOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Curve</span>
      <select bind:value={curveType} class="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm">
        <option value="all">All curves</option>
        {#each curveOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Source</span>
      <select bind:value={sourceStatus} class="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm">
        <option value="all">All sources</option>
        {#each sourceOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Confidence</span>
      <select bind:value={confidence} class="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm">
        <option value="all">All labels</option>
        {#each confidenceOptions as value (value)}
          <option value={value}>{labelForConfidence(value)}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Scope</span>
      <select bind:value={scope} class="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm">
        <option value="all">All scopes</option>
        {#each scopeOptions as value (value)}
          <option value={value}>{labelForScope(value)}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-slate-600">
      <span class="mb-1 block font-semibold text-slate-700">Sort</span>
      <select bind:value={sortMode} class="w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm">
        <option value="triage">Close and thin first</option>
        <option value="confidence-strong">Strongest first</option>
        <option value="candidates-desc">Most candidates</option>
        <option value="finding">Finding id</option>
      </select>
    </label>
  </div>

  <p class="text-xs text-slate-500">
    Showing {filteredRows.length} of {rows.length} scope-matched AIC rows.
  </p>

  <div class="overflow-x-auto rounded-md border border-slate-200 bg-white">
    <table class="w-full min-w-[1120px] border-collapse text-sm">
      <thead class="bg-slate-50 text-left text-xs uppercase text-slate-500">
        <tr>
          <th class="sticky left-0 z-10 w-80 bg-slate-50 px-3 py-2">Finding</th>
          <th class="px-3 py-2">Confidence</th>
          {#each columns as column (column.id)}
            <th class="min-w-36 px-3 py-2" title={column.description}>
              {column.label}
            </th>
          {/each}
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-200">
        {#each filteredRows as row (row.selection_id)}
          <tr>
            <td class="sticky left-0 z-10 w-80 bg-white px-3 py-2 align-top">
              <a class="font-mono text-[11px] text-slate-900" href={row.finding_href}>
                {row.finding_id.replace("finding.", "")}
              </a>
              <p class="mt-1 text-[11px] text-slate-500">
                <a class="text-slate-600 hover:text-accent" href={row.paper_href}>
                  {row.paper_label}
                </a>
              </p>
              <div class="mt-2 flex flex-wrap gap-1">
                <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                  {row.species}
                </span>
                <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                  {row.curve_type.replace(/_/g, " ")}
                </span>
                <span class={`rounded px-1.5 py-0.5 text-[10px] ${sourceClass(row.source_status)}`}>
                  {row.source_status}
                </span>
              </div>
            </td>
            <td class="px-3 py-2 align-top">
              <span
                class={`rounded px-1.5 py-0.5 text-[10px] uppercase ${confidenceClass(row.confidence_label)}`}
                title={confidenceDefinitions[row.confidence_label]?.description ?? ""}
              >
                {labelForConfidence(row.confidence_label)}
              </span>
              <p class="mt-1 text-[11px] text-slate-500">
                {row.n_candidate_fits} candidates
              </p>
              <span
                class={`mt-2 inline-block rounded px-1.5 py-0.5 text-[10px] uppercase ${scopeClass(row.comparison_scope)}`}
                title={scopeDefinitions[row.comparison_scope]?.description ?? ""}
              >
                {labelForScope(row.comparison_scope)}
              </span>
              {#if row.interpretation_warning}
                <p
                  class="mt-2 text-[11px] text-warn"
                  title={row.interpretation_warning.message}
                >
                  {row.interpretation_warning.warning_type.replace(/_/g, " ")}
                </p>
              {/if}
            </td>
            {#each columns as column (column.id)}
              {@const cell = row.cells[column.id]}
              <td class={cellClass(cell)}>
                {#if cell}
                  <div class="flex items-start justify-between gap-2">
                    <div>
                      <p class="font-mono text-xs text-slate-900">
                        {fmt(cell.aic)}
                      </p>
                      <p class="mt-0.5 text-[11px] text-slate-500">
                        dAIC {fmt(cell.delta_from_best)}
                      </p>
                    </div>
                    {#if cell.is_winner}
                      <span class="rounded bg-white px-1.5 py-0.5 text-[10px] uppercase text-ok">
                        winner
                      </span>
                    {/if}
                  </div>
                  <p class="mt-1 max-w-36 truncate font-mono text-[10px] text-slate-500" title={cell.variant_id}>
                    {cell.variant_label}
                  </p>
                  {#if cell.caveat_tags.length > 0}
                    <ul class="mt-1 flex flex-wrap gap-1">
                      {#each cell.caveat_tags as tag (tag)}
                        <li
                          class="rounded bg-warn-soft px-1.5 py-0.5 text-[10px] text-warn"
                          title={caveatDefinitions[tag]?.description ?? tag}
                        >
                          {labelForCaveat(tag)}
                        </li>
                      {/each}
                    </ul>
                  {/if}
                {:else}
                  <span class="text-xs text-slate-400">-</span>
                {/if}
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
