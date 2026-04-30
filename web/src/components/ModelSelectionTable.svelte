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

  type ScopeWinner = {
    selection_id: string;
    comparison_scope: string;
    best_variant_id: string;
    best_variant_label: string;
    best_aic: number | null;
    delta_aic_to_next: number | null;
    confidence_label?: string;
  };

  type ModelSelectionRow = {
    selection_id: string;
    selection_level: string;
    finding_id: string;
    finding_href: string;
    paper_id: string;
    paper_href: string;
    paper_label: string;
    species: string;
    protocol_name: string;
    curve_type: string;
    source_data_level: string;
    stratification_label: string;
    best_fit_id: string;
    best_variant_id: string;
    best_variant_label: string;
    best_family_label: string;
    best_aic: number | null;
    delta_aic_to_next: number | null;
    confidence_label?: string;
    comparison_scope: string;
    n_candidate_fits: number;
    has_mixed_aic_scopes: boolean;
    scope_selection_ids: string[];
    candidate_scope_counts: Record<string, number>;
    candidate_variant_ids: string[];
    candidate_comparison_scopes: string[];
    scope_winners: ScopeWinner[];
    best_caveat_tags: string[];
    candidate_caveat_tags: string[];
    interpretation_warning?: {
      warning_type: string;
      severity: string;
      message: string;
    } | null;
  };

  let {
    rows,
    caveatDefinitions = {},
    confidenceDefinitions = {},
    scopeDefinitions = {},
  }: {
    rows: ModelSelectionRow[];
    caveatDefinitions?: Record<string, CaveatDefinition>;
    confidenceDefinitions?: Record<string, ConfidenceDefinition>;
    scopeDefinitions?: Record<string, ScopeDefinition>;
  } = $props();

  let query = $state("");
  let species = $state("all");
  let family = $state("all");
  let scope = $state("all");
  let confidence = $state("all");
  let comparability = $state("all");
  let caveat = $state("all");
  let sortMode = $state("delta-desc");

  const speciesOptions = $derived(
    Array.from(new Set(rows.map((row) => row.species).filter(Boolean))).sort(),
  );
  const familyOptions = $derived(
    Array.from(new Set(rows.map((row) => row.best_family_label))).sort(),
  );
  const caveatOptions = $derived(
    Array.from(
      new Set(rows.flatMap((row) => row.candidate_caveat_tags)),
    ).sort(),
  );
  const scopeOptions = $derived(
    Array.from(new Set(rows.map((row) => row.comparison_scope).filter(Boolean))).sort(),
  );
  const confidenceOptions = $derived(
    Array.from(
      new Set(rows.map((row) => row.confidence_label).filter(Boolean)),
    ).sort(),
  );
  const mixedScopeCount = $derived(
    rows.filter((row) => row.has_mixed_aic_scopes).length,
  );

  function labelForTag(tag: string): string {
    return caveatDefinitions[tag]?.label ?? tag.replace(/_/g, " ");
  }

  function labelForConfidence(label: string | undefined, delta: number | null): string {
    if (label) return confidenceDefinitions[label]?.label ?? label.replace(/_/g, " ");
    if (delta === null) return "single candidate";
    if (delta >= 10) return "decisive";
    if (delta >= 2) return "supported";
    return "close";
  }

  function labelForScope(value: string): string {
    return scopeDefinitions[value]?.label ?? value.replace(/_/g, " ");
  }

  function fmt(value: number | null | undefined, digits = 1): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return "-";
    return value.toFixed(digits);
  }

  function haystack(row: ModelSelectionRow): string {
    return [
      row.selection_id,
      row.finding_id,
      row.paper_label,
      row.species,
      row.protocol_name,
      row.curve_type,
      row.source_data_level,
      row.stratification_label,
      row.best_fit_id,
      row.best_variant_id,
      row.confidence_label,
      row.comparison_scope,
      row.has_mixed_aic_scopes ? "mixed scopes" : "single scope",
      ...row.candidate_variant_ids,
      ...row.candidate_comparison_scopes,
      ...row.candidate_caveat_tags,
      ...row.scope_winners.map((winner) => [
        winner.comparison_scope,
        winner.best_variant_id,
        winner.best_variant_label,
        winner.confidence_label,
      ].join(" ")),
      row.interpretation_warning?.warning_type,
    ]
      .join(" ")
      .toLowerCase();
  }

  const filteredRows = $derived.by(() => {
    const q = query.trim().toLowerCase();
    const out = rows.filter((row) => {
      if (q && !haystack(row).includes(q)) return false;
      if (species !== "all" && row.species !== species) return false;
      if (family !== "all" && row.best_family_label !== family) return false;
      if (scope !== "all" && row.comparison_scope !== scope) return false;
      if (confidence !== "all" && row.confidence_label !== confidence) return false;
      if (comparability === "mixed" && !row.has_mixed_aic_scopes) return false;
      if (comparability === "single" && row.has_mixed_aic_scopes) return false;
      if (comparability === "warning" && !row.interpretation_warning) return false;
      if (caveat !== "all" && !row.candidate_caveat_tags.includes(caveat)) {
        return false;
      }
      return true;
    });
    return out.sort((a, b) => {
      if (sortMode === "aic-asc") {
        return (a.best_aic ?? Infinity) - (b.best_aic ?? Infinity);
      }
      if (sortMode === "candidates-desc") {
        return b.n_candidate_fits - a.n_candidate_fits;
      }
      const da = a.delta_aic_to_next ?? -1;
      const db = b.delta_aic_to_next ?? -1;
      return db - da || a.finding_id.localeCompare(b.finding_id);
    });
  });
</script>

<div class="space-y-3">
  <div class="grid grid-cols-1 gap-2 lg:grid-cols-[1.4fr_repeat(8,minmax(0,1fr))]">
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Search</span>
      <input
        bind:value={query}
        type="search"
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        placeholder="finding, paper, variant, caveat"
      />
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Species</span>
      <select
        bind:value={species}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm"
      >
        <option value="all">All species</option>
        {#each speciesOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Winner family</span>
      <select
        bind:value={family}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm"
      >
        <option value="all">All families</option>
        {#each familyOptions as value (value)}
          <option value={value}>{value}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Caveat</span>
      <select
        bind:value={caveat}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm"
      >
        <option value="all">All caveats</option>
        {#each caveatOptions as value (value)}
          <option value={value}>{labelForTag(value)}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Scope</span>
      <select
        bind:value={scope}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm"
      >
        <option value="all">All scopes</option>
        {#each scopeOptions as value (value)}
          <option value={value}>{labelForScope(value)}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Confidence</span>
      <select
        bind:value={confidence}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm"
      >
        <option value="all">All labels</option>
        {#each confidenceOptions as value (value)}
          <option value={value}>{labelForConfidence(value, null)}</option>
        {/each}
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Comparability</span>
      <select
        bind:value={comparability}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm"
      >
        <option value="all">All scope sets</option>
        <option value="mixed">Mixed scopes</option>
        <option value="single">Single scope</option>
        <option value="warning">Warnings only</option>
      </select>
    </label>
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Sort</span>
      <select
        bind:value={sortMode}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-sm"
      >
        <option value="delta-desc">Largest AIC gap</option>
        <option value="aic-asc">Lowest AIC</option>
        <option value="candidates-desc">Most candidates</option>
      </select>
    </label>
  </div>

  <p class="text-xs text-fg-muted">
    Showing {filteredRows.length} of {rows.length} finding-level AIC winners;
    {mixedScopeCount} mix multiple comparison scopes.
  </p>

  <div class="overflow-x-auto rounded-md border border-rule bg-surface-raised">
    <table class="w-full min-w-[1100px] border-collapse text-sm">
      <thead class="bg-surface text-left text-xs uppercase tracking-wide text-fg-muted">
        <tr>
          <th class="sticky left-0 z-10 w-72 bg-surface px-3 py-2 shadow-[1px_0_0_0_#e2e8f0]">Finding</th>
          <th class="px-3 py-2">Paper</th>
          <th class="px-3 py-2">Species</th>
          <th class="px-3 py-2">Stratification</th>
          <th class="px-3 py-2">Winner</th>
          <th class="px-3 py-2 text-right">AIC</th>
          <th class="px-3 py-2 text-right">Delta</th>
          <th class="px-3 py-2">Confidence</th>
          <th class="px-3 py-2">Scope</th>
          <th class="px-3 py-2">Comparability</th>
          <th class="px-3 py-2">Scope winners</th>
          <th class="px-3 py-2">Caveats</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-rule">
        {#each filteredRows as row (row.selection_id)}
          <tr>
            <td class="sticky left-0 z-10 w-72 max-w-72 bg-surface-raised px-3 py-2 shadow-[1px_0_0_0_#e2e8f0]">
              <a class="font-mono text-[11px] text-fg" href={row.finding_href}>
                {row.finding_id.replace("finding.", "")}
              </a>
              <p class="mt-0.5 text-[11px] text-fg-muted">
                {row.curve_type.replace(/_/g, " ")} · {row.protocol_name}
              </p>
            </td>
            <td class="px-3 py-2 text-xs">
              <a class="text-fg hover:text-accent" href={row.paper_href}>
                {row.paper_label}
              </a>
            </td>
            <td class="px-3 py-2 text-xs text-fg-muted">{row.species}</td>
            <td class="px-3 py-2 text-xs text-fg-muted">
              {row.stratification_label}
            </td>
            <td class="px-3 py-2">
              <span class="font-mono text-[11px] text-fg">
                {row.best_variant_label}
              </span>
              <p class="mt-0.5 text-[11px] text-fg-muted">
                {row.best_family_label} · {row.n_candidate_fits} candidates
              </p>
            </td>
            <td class="px-3 py-2 text-right font-mono">{fmt(row.best_aic)}</td>
            <td class="px-3 py-2 text-right">
              <span class="font-mono">{fmt(row.delta_aic_to_next)}</span>
            </td>
            <td class="px-3 py-2">
              <span
                class="rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] uppercase text-fg-muted"
                title={confidenceDefinitions[row.confidence_label ?? ""]?.description ?? ""}
              >
                {labelForConfidence(row.confidence_label, row.delta_aic_to_next)}
              </span>
            </td>
            <td class="px-3 py-2">
              <span
                class="rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] uppercase text-fg-muted"
                title={scopeDefinitions[row.comparison_scope]?.description ?? ""}
              >
                {labelForScope(row.comparison_scope)}
              </span>
              {#if row.interpretation_warning}
                <p
                  class="mt-1 text-[11px] text-warn"
                  title={row.interpretation_warning.message}
                >
                  {row.interpretation_warning.warning_type.replace(/_/g, " ")}
                </p>
              {/if}
            </td>
            <td class="px-3 py-2">
              <span
                class={`rounded px-1.5 py-0.5 text-[10px] uppercase ${row.has_mixed_aic_scopes ? "bg-warn-soft text-warn" : "bg-ok-soft text-ok"}`}
              >
                {row.has_mixed_aic_scopes ? "mixed scopes" : "single scope"}
              </span>
              <ul class="mt-1 flex max-w-60 flex-wrap gap-1">
                {#each row.candidate_comparison_scopes as value (value)}
                  <li
                    class="rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] text-fg-muted"
                    title={scopeDefinitions[value]?.description ?? ""}
                  >
                    {labelForScope(value)}
                    {#if row.candidate_scope_counts[value]}
                      <span class="font-mono"> {row.candidate_scope_counts[value]}</span>
                    {/if}
                  </li>
                {/each}
              </ul>
            </td>
            <td class="px-3 py-2">
              {#if row.scope_winners.length === 0}
                <span class="text-xs text-fg-muted">-</span>
              {:else}
                <ul class="space-y-1">
                  {#each row.scope_winners as winner (winner.selection_id)}
                    <li class="text-[11px] text-fg-muted">
                      <span class="font-semibold text-fg-secondary">
                        {labelForScope(winner.comparison_scope)}
                      </span>
                      <span class="font-mono">
                        {" "}{winner.best_variant_label}
                      </span>
                      <span class="font-mono text-fg-muted">
                        {" "}AIC {fmt(winner.best_aic)}
                      </span>
                    </li>
                  {/each}
                </ul>
              {/if}
            </td>
            <td class="px-3 py-2">
              {#if row.best_caveat_tags.length === 0}
                <span class="text-xs text-fg-muted">-</span>
              {:else}
                <ul class="flex max-w-72 flex-wrap gap-1">
                  {#each row.best_caveat_tags as tag (tag)}
                    <li
                      class="rounded bg-warn-soft px-2 py-0.5 text-body-xs text-warn"
                      title={caveatDefinitions[tag]?.description ?? tag}
                    >
                      {labelForTag(tag)}
                    </li>
                  {/each}
                </ul>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
