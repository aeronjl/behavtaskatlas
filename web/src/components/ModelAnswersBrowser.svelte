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

  type AnswerRow = {
    best_aic: number | null;
    best_caveat_tags: string[];
    best_family_label: string;
    best_fit_id: string;
    best_variant_id: string;
    best_variant_label: string;
    candidate_caveat_tags: string[];
    candidate_comparison_scopes: string[];
    candidate_variant_ids: string[];
    comparison_scope: string;
    confidence_label?: string;
    curve_type: string;
    delta_aic_to_next: number | null;
    finding_href: string;
    finding_id: string;
    has_mixed_aic_scopes: boolean;
    n_candidate_fits: number;
    paper_href: string;
    paper_label: string;
    protocol_name: string;
    selection_id: string;
    source_data_level: string;
    species: string;
    stratification_label: string;
    task_family: string;
  };

  type RoadmapItem = {
    caveat_tags?: string[];
    issue_type: string;
    priority_label: string;
    rank: number;
    recommended_action?: string | null;
    status: string;
    target_id: string;
    target_type: string;
  };

  type Option = {
    value: string;
    label: string;
    count: number;
  };

  let {
    rows,
    roadmapItems = [],
    caveatDefinitions = {},
    confidenceDefinitions = {},
    scopeDefinitions = {},
  }: {
    rows: AnswerRow[];
    roadmapItems?: RoadmapItem[];
    caveatDefinitions?: Record<string, CaveatDefinition>;
    confidenceDefinitions?: Record<string, ConfidenceDefinition>;
    scopeDefinitions?: Record<string, ScopeDefinition>;
  } = $props();

  const questionLabels: Record<string, string> = {
    winners: "Winners",
    close: "Close calls",
    caveats: "Caveats",
    process: "Process models",
  };

  const sortLabels: Record<string, string> = {
    "delta-desc": "Largest AIC gap",
    "close-first": "Closest decision",
    "candidates-desc": "Most candidates",
    "paper-asc": "Paper A-Z",
  };

  function initialParam(name: string): string | null {
    if (typeof window === "undefined") return null;
    return new URLSearchParams(window.location.search).get(name);
  }

  const initialQuestion = initialParam("model_question") ?? "winners";
  const initialSort = initialParam("model_sort") ?? "delta-desc";

  let query = $state(initialParam("model_q") ?? "");
  let question = $state(questionLabels[initialQuestion] ? initialQuestion : "winners");
  let taskFamily = $state(initialParam("model_family") ?? "all");
  let species = $state(initialParam("model_species") ?? "all");
  let curveType = $state(initialParam("model_curve") ?? "all");
  let winnerFamily = $state(initialParam("model_winner") ?? "all");
  let confidence = $state(initialParam("model_confidence") ?? "all");
  let sortMode = $state(sortLabels[initialSort] ? initialSort : "delta-desc");

  const queryTokens = $derived(
    query
      .toLowerCase()
      .split(/\s+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0),
  );

  const activeFilterCount = $derived(
    (queryTokens.length > 0 ? 1 : 0) +
      (question === "winners" ? 0 : 1) +
      (taskFamily === "all" ? 0 : 1) +
      (species === "all" ? 0 : 1) +
      (curveType === "all" ? 0 : 1) +
      (winnerFamily === "all" ? 0 : 1) +
      (confidence === "all" ? 0 : 1),
  );

  function readable(value: string | null | undefined): string {
    if (!value) return "-";
    if (value === "non-human-primate") return "NHP";
    if (value === "figure-source-data") return "figure source data";
    if (value === "processed-trial") return "processed trials";
    if (value === "raw-trial") return "raw trials";
    return value.replace(/[_-]/g, " ");
  }

  function labelForConfidence(value: string | undefined): string {
    if (!value) return "unlabelled";
    return confidenceDefinitions[value]?.label ?? readable(value);
  }

  function labelForScope(value: string): string {
    return scopeDefinitions[value]?.label ?? readable(value);
  }

  function labelForCaveat(value: string): string {
    return caveatDefinitions[value]?.label ?? readable(value);
  }

  function fmt(value: number | null | undefined, digits = 1): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return "-";
    return value.toFixed(digits);
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

  const taskOptions = $derived(countOptions(rows.map((row) => row.task_family)));
  const speciesOptions = $derived(countOptions(rows.map((row) => row.species)));
  const curveOptions = $derived(countOptions(rows.map((row) => row.curve_type)));
  const winnerOptions = $derived(countOptions(rows.map((row) => row.best_family_label)));
  const confidenceOptions = $derived(
    countOptions(rows.map((row) => row.confidence_label ?? "")),
  );

  const closeCount = $derived(
    rows.filter((row) => row.confidence_label === "close").length,
  );
  const caveatCount = $derived(
    rows.filter((row) => row.candidate_caveat_tags.length > 0).length,
  );
  const processCount = $derived(
    rows.filter((row) =>
      row.best_variant_id.includes("ddm") ||
      row.best_variant_id.includes("click") ||
      row.best_variant_id.includes("chronometric"),
    ).length,
  );
  const decisiveCount = $derived(
    rows.filter((row) => row.confidence_label === "decisive").length,
  );

  function syncUrl() {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const setOrDelete = (name: string, value: string, defaultValue: string) => {
      if (value && value !== defaultValue) params.set(name, value);
      else params.delete(name);
    };
    setOrDelete("model_q", query.trim(), "");
    setOrDelete("model_question", question, "winners");
    setOrDelete("model_family", taskFamily, "all");
    setOrDelete("model_species", species, "all");
    setOrDelete("model_curve", curveType, "all");
    setOrDelete("model_winner", winnerFamily, "all");
    setOrDelete("model_confidence", confidence, "all");
    setOrDelete("model_sort", sortMode, "delta-desc");
    const search = params.toString();
    const next = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(null, "", next);
    }
  }

  function updateQuery(event: Event) {
    query = (event.currentTarget as HTMLInputElement).value;
    syncUrl();
  }

  function updateSelect(event: Event, field: string) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    if (field === "task") taskFamily = value;
    if (field === "species") species = value;
    if (field === "curve") curveType = value;
    if (field === "winner") winnerFamily = value;
    if (field === "confidence") confidence = value;
    if (field === "sort") sortMode = value;
    syncUrl();
  }

  function setQuestion(value: string) {
    question = value;
    syncUrl();
  }

  function clearAll() {
    query = "";
    question = "winners";
    taskFamily = "all";
    species = "all";
    curveType = "all";
    winnerFamily = "all";
    confidence = "all";
    sortMode = "delta-desc";
    syncUrl();
  }

  function applyPreset(value: string) {
    query = "";
    question = "winners";
    taskFamily = "all";
    species = "all";
    curveType = "all";
    winnerFamily = "all";
    confidence = "all";
    sortMode = "delta-desc";
    if (value === "visual") taskFamily = "Visual contrast discrimination";
    if (value === "rdm") taskFamily = "Random-dot motion discrimination";
    if (value === "human") species = "human";
    if (value === "mouse") species = "mouse";
    if (value === "close") {
      question = "close";
      sortMode = "close-first";
    }
    if (value === "caveats") question = "caveats";
    if (value === "process") question = "process";
    syncUrl();
  }

  function hasQuestion(row: AnswerRow): boolean {
    if (question === "close") {
      return row.confidence_label === "close" || (row.delta_aic_to_next ?? Infinity) < 2;
    }
    if (question === "caveats") {
      return (
        row.candidate_caveat_tags.length > 0 ||
        row.source_data_level === "figure-source-data" ||
        row.has_mixed_aic_scopes
      );
    }
    if (question === "process") {
      return (
        row.best_variant_id.includes("ddm") ||
        row.best_variant_id.includes("click") ||
        row.best_variant_id.includes("chronometric") ||
        row.candidate_variant_ids.some((id) => id.includes("ddm") || id.includes("click"))
      );
    }
    return true;
  }

  function haystack(row: AnswerRow): string {
    return [
      row.finding_id,
      row.paper_label,
      row.species,
      row.task_family,
      row.protocol_name,
      row.curve_type,
      row.source_data_level,
      row.stratification_label,
      row.best_fit_id,
      row.best_variant_id,
      row.best_variant_label,
      row.best_family_label,
      row.comparison_scope,
      row.confidence_label,
      ...row.candidate_variant_ids,
      ...row.candidate_comparison_scopes,
      ...row.candidate_caveat_tags,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
  }

  const filteredRows = $derived.by(() => {
    const out = rows.filter((row) => {
      if (!hasQuestion(row)) return false;
      if (queryTokens.length > 0) {
        const text = haystack(row);
        if (!queryTokens.every((token) => text.includes(token))) return false;
      }
      if (taskFamily !== "all" && row.task_family !== taskFamily) return false;
      if (species !== "all" && row.species !== species) return false;
      if (curveType !== "all" && row.curve_type !== curveType) return false;
      if (winnerFamily !== "all" && row.best_family_label !== winnerFamily) return false;
      if (confidence !== "all" && row.confidence_label !== confidence) return false;
      return true;
    });
    return out.sort((a, b) => {
      if (sortMode === "close-first") {
        return (
          (a.delta_aic_to_next ?? Infinity) - (b.delta_aic_to_next ?? Infinity) ||
          a.finding_id.localeCompare(b.finding_id)
        );
      }
      if (sortMode === "candidates-desc") {
        return b.n_candidate_fits - a.n_candidate_fits || a.finding_id.localeCompare(b.finding_id);
      }
      if (sortMode === "paper-asc") {
        return a.paper_label.localeCompare(b.paper_label) || a.finding_id.localeCompare(b.finding_id);
      }
      return (
        (b.delta_aic_to_next ?? -1) - (a.delta_aic_to_next ?? -1) ||
        a.finding_id.localeCompare(b.finding_id)
      );
    });
  });

  const familyVerdicts = $derived.by(() => {
    const groups = new Map<
      string,
      {
        family: string;
        n: number;
        close: number;
        caveats: number;
        variants: Map<string, number>;
      }
    >();
    for (const row of filteredRows) {
      const family = row.task_family || "Unknown task family";
      const group =
        groups.get(family) ??
        { family, n: 0, close: 0, caveats: 0, variants: new Map<string, number>() };
      group.n += 1;
      if (row.confidence_label === "close") group.close += 1;
      if (row.candidate_caveat_tags.length > 0) group.caveats += 1;
      group.variants.set(row.best_variant_label, (group.variants.get(row.best_variant_label) ?? 0) + 1);
      groups.set(family, group);
    }
    return Array.from(groups.values())
      .map((group) => ({
        ...group,
        topVariants: Array.from(group.variants.entries())
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
          .slice(0, 3),
      }))
      .sort((a, b) => b.n - a.n || a.family.localeCompare(b.family))
      .slice(0, 5);
  });

  const topRoadmapItems = $derived(
    roadmapItems
      .slice()
      .sort((a, b) => a.rank - b.rank)
      .slice(0, 6),
  );
</script>

<section class="space-y-4">
  <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
    <div class="rounded-md border border-slate-200 bg-white p-3">
      <p class="text-xs uppercase tracking-wide text-slate-500">Finding winners</p>
      <p class="mt-1 font-mono text-2xl font-semibold text-slate-900">{rows.length}</p>
      <p class="mt-1 text-xs text-slate-500">{decisiveCount} decisive</p>
    </div>
    <div class="rounded-md border border-slate-200 bg-white p-3">
      <p class="text-xs uppercase tracking-wide text-slate-500">Close calls</p>
      <p class="mt-1 font-mono text-2xl font-semibold text-slate-900">{closeCount}</p>
      <p class="mt-1 text-xs text-slate-500">low AIC separation</p>
    </div>
    <div class="rounded-md border border-slate-200 bg-white p-3">
      <p class="text-xs uppercase tracking-wide text-slate-500">Caveated rows</p>
      <p class="mt-1 font-mono text-2xl font-semibold text-slate-900">{caveatCount}</p>
      <p class="mt-1 text-xs text-slate-500">source or proxy caveats</p>
    </div>
    <div class="rounded-md border border-slate-200 bg-white p-3">
      <p class="text-xs uppercase tracking-wide text-slate-500">Process winners</p>
      <p class="mt-1 font-mono text-2xl font-semibold text-slate-900">{processCount}</p>
      <p class="mt-1 text-xs text-slate-500">DDM, click, RT models</p>
    </div>
  </div>

  <div class="rounded-md border border-slate-200 bg-white p-4">
    <div class="flex flex-wrap gap-2 text-xs">
      {#each Object.entries(questionLabels) as [value, label] (value)}
        <button
          type="button"
          class={[
            "rounded border px-2.5 py-1 font-semibold",
            question === value
              ? "border-accent bg-accent text-white"
              : "border-slate-300 bg-white text-slate-700 hover:border-accent hover:text-accent",
          ]}
          onclick={() => setQuestion(value)}
        >
          {label}
        </button>
      {/each}
    </div>

    <div class="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1.5fr)_repeat(6,minmax(8rem,0.8fr))]">
      <label class="text-xs text-slate-600">
        <span class="mb-1 block font-semibold text-slate-700">Search</span>
        <input
          value={query}
          oninput={updateQuery}
          type="search"
          class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          placeholder="paper, task, model, caveat"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
        />
      </label>
      <label class="text-xs text-slate-600">
        <span class="mb-1 block font-semibold text-slate-700">Task</span>
        <select value={taskFamily} onchange={(event) => updateSelect(event, "task")} class="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm">
          <option value="all">All tasks</option>
          {#each taskOptions as option (option.value)}
            <option value={option.value}>{option.label} · {option.count}</option>
          {/each}
        </select>
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
        <span class="mb-1 block font-semibold text-slate-700">Curve</span>
        <select value={curveType} onchange={(event) => updateSelect(event, "curve")} class="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm">
          <option value="all">All curves</option>
          {#each curveOptions as option (option.value)}
            <option value={option.value}>{option.label} · {option.count}</option>
          {/each}
        </select>
      </label>
      <label class="text-xs text-slate-600">
        <span class="mb-1 block font-semibold text-slate-700">Winner</span>
        <select value={winnerFamily} onchange={(event) => updateSelect(event, "winner")} class="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm">
          <option value="all">All winners</option>
          {#each winnerOptions as option (option.value)}
            <option value={option.value}>{option.label} · {option.count}</option>
          {/each}
        </select>
      </label>
      <label class="text-xs text-slate-600">
        <span class="mb-1 block font-semibold text-slate-700">Confidence</span>
        <select value={confidence} onchange={(event) => updateSelect(event, "confidence")} class="w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-sm">
          <option value="all">All labels</option>
          {#each confidenceOptions as option (option.value)}
            <option value={option.value}>{labelForConfidence(option.value)} · {option.count}</option>
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

    <div class="mt-3 flex flex-wrap gap-2 text-xs">
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("visual")}>visual contrast</button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("rdm")}>random-dot motion</button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("human")}>human</button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("mouse")}>mouse</button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("close")}>close calls</button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("caveats")}>source caveats</button>
      <button type="button" class="rounded border border-slate-300 bg-white px-2 py-1 text-slate-700 hover:border-accent hover:text-accent" onclick={() => applyPreset("process")}>process models</button>
      {#if activeFilterCount > 0}
        <button type="button" class="rounded border border-slate-300 bg-slate-50 px-2 py-1 font-semibold text-slate-800 hover:border-accent hover:text-accent" onclick={clearAll}>
          clear {activeFilterCount}
        </button>
      {/if}
    </div>
  </div>

  <div class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(17rem,0.65fr)]">
    <div class="space-y-3">
      <p class="text-sm text-slate-600">
        Showing <span class="font-mono font-semibold text-slate-900">{filteredRows.length}</span>
        of <span class="font-mono text-slate-900">{rows.length}</span> finding-level winners.
      </p>
      {#if filteredRows.length === 0}
        <section class="rounded-md border border-slate-200 bg-white p-5 text-sm text-slate-600">
          <p>No model-selection rows match the current filters.</p>
          {#if activeFilterCount > 0}
            <button type="button" class="mt-3 rounded border border-slate-300 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-800 hover:border-accent hover:text-accent" onclick={clearAll}>
              Clear filters
            </button>
          {/if}
        </section>
      {:else}
        <ul class="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {#each filteredRows.slice(0, 24) as row (row.selection_id)}
            <li class="rounded-md border border-slate-200 bg-white p-4">
              <header class="flex min-w-0 items-start justify-between gap-3">
                <div class="min-w-0">
                  <h3 class="text-sm font-semibold leading-snug text-slate-900">
                    <a class="no-underline hover:text-accent" href={row.finding_href}>
                      {row.paper_label} · {row.stratification_label}
                    </a>
                  </h3>
                  <p class="mt-1 text-xs text-slate-500">
                    {row.task_family} · {row.protocol_name}
                  </p>
                </div>
                <span class="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase text-slate-600">
                  {labelForConfidence(row.confidence_label)}
                </span>
              </header>

              <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                <div>
                  <dt class="text-slate-500">Winner</dt>
                  <dd class="font-mono text-slate-900">{row.best_variant_label}</dd>
                </div>
                <div>
                  <dt class="text-slate-500">Delta AIC</dt>
                  <dd class="font-mono text-slate-900">{fmt(row.delta_aic_to_next)}</dd>
                </div>
                <div>
                  <dt class="text-slate-500">Scope</dt>
                  <dd class="text-slate-700">{labelForScope(row.comparison_scope)}</dd>
                </div>
                <div>
                  <dt class="text-slate-500">Candidates</dt>
                  <dd class="font-mono text-slate-900">{row.n_candidate_fits}</dd>
                </div>
              </dl>

              <div class="mt-3 flex flex-wrap gap-1 text-[11px]">
                <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{readable(row.species)}</span>
                <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{readable(row.curve_type)}</span>
                <span class="rounded bg-slate-100 px-2 py-0.5 text-slate-700">{readable(row.source_data_level)}</span>
                {#if row.has_mixed_aic_scopes}
                  <span class="rounded bg-warn-soft px-2 py-0.5 text-warn">mixed scopes</span>
                {/if}
              </div>

              {#if row.best_caveat_tags.length > 0}
                <ul class="mt-3 flex flex-wrap gap-1">
                  {#each row.best_caveat_tags as tag (tag)}
                    <li class="rounded bg-warn-soft px-2 py-0.5 text-[11px] text-warn" title={caveatDefinitions[tag]?.description ?? tag}>
                      {labelForCaveat(tag)}
                    </li>
                  {/each}
                </ul>
              {/if}

              <div class="mt-4 flex flex-wrap gap-x-3 gap-y-1 text-xs">
                <a class="font-semibold text-accent" href={row.finding_href}>Finding</a>
                <a class="text-accent" href={row.paper_href}>Paper</a>
                <span class="font-mono text-slate-500">AIC {fmt(row.best_aic)}</span>
              </div>
            </li>
          {/each}
        </ul>
        {#if filteredRows.length > 24}
          <p class="text-xs text-slate-500">Showing first 24 matching winners; use the detailed table below for the full filtered workflow.</p>
        {/if}
      {/if}
    </div>

    <aside class="space-y-4">
      <section class="rounded-md border border-slate-200 bg-white p-4">
        <h3 class="text-sm font-semibold text-slate-900">Family Verdicts</h3>
        <ul class="mt-3 space-y-3">
          {#each familyVerdicts as group (group.family)}
            <li>
              <div class="flex items-baseline justify-between gap-3">
                <p class="text-xs font-semibold text-slate-800">{group.family}</p>
                <span class="font-mono text-xs text-slate-500">{group.n}</span>
              </div>
              <ul class="mt-1 flex flex-wrap gap-1">
                {#each group.topVariants as [variant, count] (`${group.family}-${variant}`)}
                  <li class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-700">
                    {variant} <span class="font-mono">{count}</span>
                  </li>
                {/each}
              </ul>
              <p class="mt-1 text-[11px] text-slate-500">
                {group.close} close · {group.caveats} caveated
              </p>
            </li>
          {/each}
        </ul>
      </section>

      <section class="rounded-md border border-slate-200 bg-white p-4">
        <h3 class="text-sm font-semibold text-slate-900">Next Model Work</h3>
        <ul class="mt-3 space-y-3">
          {#each topRoadmapItems as item (item.rank)}
            <li>
              <div class="flex items-baseline justify-between gap-2">
                <p class="text-xs font-semibold text-slate-800">
                  {readable(item.issue_type)}
                </p>
                <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase text-slate-600">
                  {item.priority_label}
                </span>
              </div>
              <p class="mt-1 break-all font-mono text-[10px] text-slate-500">
                {item.target_id.replace("finding.", "").replace("slice.", "")}
              </p>
              {#if item.recommended_action}
                <p class="mt-1 line-clamp-2 text-[11px] text-slate-600">
                  {item.recommended_action}
                </p>
              {/if}
            </li>
          {/each}
        </ul>
      </section>
    </aside>
  </div>
</section>
