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

  type FamilyEntry = {
    id: string;
    name: string;
    description: string;
    parameter_definitions: Array<{
      name: string;
      symbol?: string | null;
      units?: string | null;
    }>;
    applicable_curve_types: string[];
    requires: string[];
  };

  type VariantEntry = {
    id: string;
    family_id: string;
    name: string;
    free_parameters: string[];
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
    families = [],
    variants = [],
  }: {
    rows: MatrixRow[];
    columns: MatrixColumn[];
    caveatDefinitions?: Record<string, CaveatDefinition>;
    confidenceDefinitions?: Record<string, ConfidenceDefinition>;
    scopeDefinitions?: Record<string, ScopeDefinition>;
    families?: FamilyEntry[];
    variants?: VariantEntry[];
  } = $props();

  // Click-to-define: clicking any variant label in a cell opens a
  // small drawer with that variant's family description, parameters,
  // requirements, and sibling variants. Replaces the standalone
  // "Families & variants" reveal with a contextual lookup that's one
  // click from the data the reader is staring at.
  const variantsById = $derived(new Map(variants.map((v) => [v.id, v])));
  const familiesById = $derived(new Map(families.map((f) => [f.id, f])));
  const variantsByFamily = $derived.by(() => {
    const map = new Map<string, VariantEntry[]>();
    for (const variant of variants) {
      const list = map.get(variant.family_id) ?? [];
      list.push(variant);
      map.set(variant.family_id, list);
    }
    return map;
  });

  let openVariantId = $state<string | null>(null);
  const openVariant = $derived(
    openVariantId ? variantsById.get(openVariantId) ?? null : null,
  );
  const openFamily = $derived(
    openVariant ? familiesById.get(openVariant.family_id) ?? null : null,
  );
  const openSiblings = $derived(
    openVariant ? variantsByFamily.get(openVariant.family_id) ?? [] : [],
  );

  function openDefinition(variantId: string) {
    openVariantId = variantId;
  }
  function closeDefinition() {
    openVariantId = null;
  }

  $effect(() => {
    if (!openVariantId) return;
    if (typeof document === "undefined") return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") closeDefinition();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  });

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
    return "bg-surface-sunken text-fg-muted";
  }

  function sourceClass(status: string): string {
    if (status === "trial-backed") return "bg-ok-soft text-ok";
    if (status === "proxy-backed") return "bg-warn-soft text-warn";
    return "bg-surface-sunken text-fg-muted";
  }

  function scopeClass(value: string): string {
    if (value === "direct_choice") return "bg-ok-soft text-ok";
    if (value === "joint_choice_rt") return "bg-accent-soft text-accent";
    if (value === "chronometric_summary" || value === "accuracy_summary") {
      return "bg-warn-soft text-warn";
    }
    return "bg-surface-sunken text-fg-muted";
  }

  function cellClass(cell: MatrixCell | null): string {
    const base = "min-w-36 px-3 py-2 align-top";
    if (!cell) return `${base} bg-surface text-fg-subtle`;
    if (cell.is_winner) return `${base} bg-ok-soft`;
    return `${base} bg-surface-raised`;
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
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Search</span>
      <input
        bind:value={query}
        type="search"
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        placeholder="finding, paper, model, caveat"
      />
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Species</span>
      <select bind:value={species} class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm">
        <option value="all">All species</option>
        {#each speciesOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Family</span>
      <select bind:value={taskFamily} class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm">
        <option value="all">All families</option>
        {#each familyOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Curve</span>
      <select bind:value={curveType} class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm">
        <option value="all">All curves</option>
        {#each curveOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Source</span>
      <select bind:value={sourceStatus} class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm">
        <option value="all">All sources</option>
        {#each sourceOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Confidence</span>
      <select bind:value={confidence} class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm">
        <option value="all">All labels</option>
        {#each confidenceOptions as value (value)}
          <option value={value}>{labelForConfidence(value)}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Scope</span>
      <select bind:value={scope} class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm">
        <option value="all">All scopes</option>
        {#each scopeOptions as value (value)}
          <option value={value}>{labelForScope(value)}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Sort</span>
      <select bind:value={sortMode} class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm">
        <option value="triage">Close and thin first</option>
        <option value="confidence-strong">Strongest first</option>
        <option value="candidates-desc">Most candidates</option>
        <option value="finding">Finding id</option>
      </select>
    </label>
  </div>

  <p class="text-xs text-fg-muted">
    Showing {filteredRows.length} of {rows.length} scope-matched AIC rows.
  </p>

  <div class="overflow-x-auto rounded-md border border-rule bg-surface-raised">
    <table class="w-full min-w-[1120px] border-collapse text-sm">
      <thead class="bg-surface text-left text-xs uppercase text-fg-muted">
        <tr>
          <th class="sticky left-0 z-10 w-80 bg-surface px-3 py-2 shadow-[1px_0_0_0_#e2e8f0]">Finding</th>
          <th class="px-3 py-2">Confidence</th>
          {#each columns as column (column.id)}
            <th class="min-w-36 px-3 py-2" title={column.description}>
              {column.label}
            </th>
          {/each}
        </tr>
      </thead>
      <tbody class="divide-y divide-rule">
        {#each filteredRows as row (row.selection_id)}
          <tr>
            <td class="sticky left-0 z-10 w-80 bg-surface-raised px-3 py-2 align-top shadow-[1px_0_0_0_#e2e8f0]">
              <a class="font-mono text-[11px] text-fg" href={row.finding_href}>
                {row.finding_id.replace("finding.", "")}
              </a>
              <p class="mt-1 text-[11px] text-fg-muted">
                <a class="text-fg-muted hover:text-accent" href={row.paper_href}>
                  {row.paper_label}
                </a>
              </p>
              <div class="mt-2 flex flex-wrap gap-1">
                <span class="rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] text-fg-muted">
                  {row.species}
                </span>
                <span class="rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] text-fg-muted">
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
              <p class="mt-1 text-[11px] text-fg-muted">
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
                      <p class="font-mono text-xs text-fg">
                        {fmt(cell.aic)}
                      </p>
                      <p class="mt-0.5 text-[11px] text-fg-muted">
                        dAIC {fmt(cell.delta_from_best)}
                      </p>
                    </div>
                    {#if cell.is_winner}
                      <span class="rounded bg-surface-raised px-1.5 py-0.5 text-[10px] uppercase text-ok">
                        winner
                      </span>
                    {/if}
                  </div>
                  <button
                    type="button"
                    class="mt-1 inline-flex max-w-36 truncate rounded border border-rule bg-surface-raised px-1.5 py-0.5 font-mono text-[10px] text-fg-muted transition-colors hover:border-accent hover:text-accent"
                    title={`${cell.variant_id} — click for family definition`}
                    onclick={() => openDefinition(cell.variant_id)}
                  >
                    {cell.variant_label}
                  </button>
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
                  <span class="text-xs text-fg-subtle">-</span>
                {/if}
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

{#if openVariantId && openFamily && openVariant}
  <div
    class="fixed inset-0 z-40 flex items-stretch justify-end bg-fg/30 animate-fade-in"
    onclick={closeDefinition}
    onkeydown={(event) => event.key === "Escape" && closeDefinition()}
    role="dialog"
    aria-modal="true"
    aria-labelledby="family-popover-title"
    tabindex="-1"
  >
    <aside
      class="flex w-full max-w-md flex-col gap-3 overflow-y-auto border-l border-rule bg-surface-raised p-5 shadow-2xl"
      onclick={(event) => event.stopPropagation()}
      onkeydown={(event) => event.stopPropagation()}
      role="presentation"
    >
      <header class="flex items-baseline justify-between gap-3">
        <div>
          <p class="text-eyebrow uppercase text-fg-muted">
            {openFamily.applicable_curve_types.join(" · ")}
          </p>
          <h2 id="family-popover-title" class="mt-1 text-h3 text-fg">
            {openFamily.name}
          </h2>
          <p class="mt-1 font-mono text-mono-id text-fg-muted">{openFamily.id}</p>
        </div>
        <button
          type="button"
          class="rounded border border-rule-strong bg-surface-raised px-2 py-1 text-body-xs text-fg-secondary hover:border-rule-emphasis hover:text-accent"
          onclick={closeDefinition}
          aria-label="Close family definition"
        >
          Close
        </button>
      </header>
      <p class="text-body text-fg-secondary">{openFamily.description}</p>

      <section>
        <h3 class="mb-1 text-eyebrow uppercase text-fg-muted">Parameters</h3>
        <ul class="space-y-1 text-body-xs">
          {#each openFamily.parameter_definitions as p (p.name)}
            <li>
              <span class="font-mono font-semibold text-fg">{p.symbol ?? p.name}</span>
              <span class="ml-1 text-fg-secondary">{p.name}</span>
              {#if p.units}
                <span class="ml-1 text-fg-muted">[{p.units}]</span>
              {/if}
            </li>
          {/each}
        </ul>
      </section>

      <section>
        <h3 class="mb-1 text-eyebrow uppercase text-fg-muted">Requires</h3>
        <ul class="flex flex-wrap gap-1">
          {#each openFamily.requires as requirement (requirement)}
            <li class="rounded bg-surface-sunken px-2 py-0.5 font-mono text-mono-id text-fg-secondary">
              {requirement}
            </li>
          {/each}
        </ul>
      </section>

      <section>
        <h3 class="mb-1 text-eyebrow uppercase text-fg-muted">
          Variants ({openSiblings.length})
        </h3>
        <ul class="space-y-1.5 text-body-xs">
          {#each openSiblings as sibling (sibling.id)}
            {@const isCurrent = sibling.id === openVariantId}
            <li
              class={[
                "rounded border px-2 py-1.5",
                isCurrent
                  ? "border-accent bg-accent-soft"
                  : "border-rule bg-surface",
              ]}
            >
              <p class="flex items-baseline justify-between gap-2">
                <span class="font-mono text-fg">
                  {sibling.id.replace("model_variant.", "")}
                </span>
                {#if isCurrent}
                  <span class="text-mono-id text-accent">selected</span>
                {/if}
              </p>
              <p class="text-fg-secondary">{sibling.name}</p>
              <p class="font-mono text-mono-id text-fg-muted">
                free = [{sibling.free_parameters.join(", ")}]
              </p>
            </li>
          {/each}
        </ul>
      </section>

      <p class="mt-auto text-mono-id text-fg-muted">
        Press Esc to close. Family definitions live under
        <code class="rounded bg-surface-sunken px-1">model_families/</code>
        in the repo.
      </p>
    </aside>
  </div>
{/if}
