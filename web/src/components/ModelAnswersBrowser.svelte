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

  const confidenceSteps = ["single_candidate", "close", "supported", "decisive"];

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

  function winnerKey(variantId: string): string {
    const id = variantId.toLowerCase();
    if (id.includes("ddm")) return "ddm";
    if (id.includes("click")) return "click";
    if (id.includes("sdt")) return "sdt";
    if (id.includes("chronometric")) return "chronometric";
    if (id.includes("logistic")) return "logistic";
    if (id.includes("bernoulli") || id.includes("rate")) return "rate";
    if (id.includes("accuracy")) return "accuracy";
    return "other";
  }

  function winnerShortLabel(variantId: string): string {
    const key = winnerKey(variantId);
    if (key === "ddm") return "DDM";
    if (key === "click") return "Clicks";
    if (key === "sdt") return "SDT";
    if (key === "chronometric") return "RT";
    if (key === "logistic") return "Logistic";
    if (key === "rate") return "Rate";
    if (key === "accuracy") return "Accuracy";
    return "Other";
  }

  function winnerClass(keyOrVariant: string): string {
    const key = keyOrVariant.startsWith("model_variant.") ? winnerKey(keyOrVariant) : keyOrVariant;
    if (key === "ddm") return "bg-violet-600";
    if (key === "click") return "bg-amber-500";
    if (key === "sdt") return "bg-blue-600";
    if (key === "chronometric") return "bg-teal-500";
    if (key === "logistic") return "bg-sky-500";
    if (key === "rate") return "bg-emerald-500";
    if (key === "accuracy") return "bg-rose-500";
    return "bg-slate-400";
  }

  function winnerSoftClass(keyOrVariant: string): string {
    const key = keyOrVariant.startsWith("model_variant.") ? winnerKey(keyOrVariant) : keyOrVariant;
    if (key === "ddm") return "bg-violet-50 text-violet-700 ring-violet-200";
    if (key === "click") return "bg-amber-50 text-amber-800 ring-amber-200";
    if (key === "sdt") return "bg-blue-50 text-blue-700 ring-blue-200";
    if (key === "chronometric") return "bg-teal-50 text-teal-700 ring-teal-200";
    if (key === "logistic") return "bg-sky-50 text-sky-700 ring-sky-200";
    if (key === "rate") return "bg-emerald-50 text-emerald-700 ring-emerald-200";
    if (key === "accuracy") return "bg-rose-50 text-rose-700 ring-rose-200";
    return "bg-slate-100 text-slate-700 ring-slate-200";
  }

  function confidenceClass(label: string | undefined): string {
    if (label === "decisive") return "bg-emerald-500";
    if (label === "supported") return "bg-sky-500";
    if (label === "close") return "bg-amber-500";
    if (label === "single_candidate") return "bg-slate-500";
    return "bg-slate-300";
  }

  function confidenceSoftClass(label: string | undefined): string {
    if (label === "decisive") return "bg-emerald-50 text-emerald-700 ring-emerald-200";
    if (label === "supported") return "bg-sky-50 text-sky-700 ring-sky-200";
    if (label === "close") return "bg-amber-50 text-amber-800 ring-amber-200";
    if (label === "single_candidate") return "bg-slate-100 text-slate-700 ring-slate-200";
    return "bg-slate-100 text-slate-600 ring-slate-200";
  }

  function sourceClass(level: string): string {
    if (level === "raw-trial") return "bg-emerald-500";
    if (level === "processed-trial") return "bg-sky-500";
    if (level === "figure-source-data") return "bg-amber-500";
    return "bg-slate-300";
  }

  function sourceShortLabel(level: string): string {
    if (level === "raw-trial") return "raw";
    if (level === "processed-trial") return "trials";
    if (level === "figure-source-data") return "figure";
    return "summary";
  }

  function sourceSoftClass(level: string): string {
    if (level === "raw-trial") return "bg-emerald-50 text-emerald-700 ring-emerald-200";
    if (level === "processed-trial") return "bg-sky-50 text-sky-700 ring-sky-200";
    if (level === "figure-source-data") return "bg-amber-50 text-amber-800 ring-amber-200";
    return "bg-slate-100 text-slate-700 ring-slate-200";
  }

  function uniqueCaveatTags(row: AnswerRow): string[] {
    return Array.from(new Set([...row.best_caveat_tags, ...row.candidate_caveat_tags]));
  }

  function caveatCount(row: AnswerRow): number {
    return uniqueCaveatTags(row).length;
  }

  function aicWidth(value: number | null | undefined, max: number): string {
    if (!value || max <= 0) return "0%";
    return `${Math.max(8, Math.round((Math.log1p(value) / Math.log1p(max)) * 100))}%`;
  }

  function percent(value: number, total: number): string {
    if (value <= 0 || total <= 0) return "0%";
    return `${Math.max(3, Math.round((value / total) * 100))}%`;
  }

  function candidatePips(row: AnswerRow, maxCandidates: number): Array<{ index: number; active: boolean }> {
    const total = Math.max(1, Math.min(8, maxCandidates));
    return Array.from({ length: total }, (_, index) => ({
      index,
      active: index < row.n_candidate_fits,
    }));
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
  const caveatedRowCount = $derived(
    rows.filter((row) => caveatCount(row) > 0).length,
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
  const maxDelta = $derived(Math.max(1, ...rows.map((row) => row.delta_aic_to_next ?? 0)));
  const maxCandidateCount = $derived(Math.max(1, ...rows.map((row) => row.n_candidate_fits)));

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
        mixed: number;
        winners: Map<string, { label: string; count: number }>;
      }
    >();
    for (const row of filteredRows) {
      const family = row.task_family || "Unknown task family";
      const group =
        groups.get(family) ??
        { family, n: 0, close: 0, caveats: 0, mixed: 0, winners: new Map<string, { label: string; count: number }>() };
      group.n += 1;
      if (row.confidence_label === "close") group.close += 1;
      if (caveatCount(row) > 0) group.caveats += 1;
      if (row.has_mixed_aic_scopes) group.mixed += 1;
      const key = winnerKey(row.best_variant_id);
      const winner = group.winners.get(key) ?? { label: winnerShortLabel(row.best_variant_id), count: 0 };
      winner.count += 1;
      group.winners.set(key, winner);
      groups.set(family, group);
    }
    return Array.from(groups.values())
      .map((group) => ({
        ...group,
        winnerSegments: Array.from(group.winners.entries())
          .map(([key, winner]) => ({ key, ...winner }))
          .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label)),
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
      <p class="mt-1 font-mono text-2xl font-semibold text-slate-900">{caveatedRowCount}</p>
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
                <span
                  class={[
                    "shrink-0 rounded px-1.5 py-0.5 text-[10px] uppercase ring-1",
                    confidenceSoftClass(row.confidence_label),
                  ]}
                >
                  {labelForConfidence(row.confidence_label)}
                </span>
              </header>

              <div
                data-testid="model-glyph-strip"
                class="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3"
                aria-label={`${row.paper_label} model-selection glyphs`}
              >
                <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div class="min-w-0">
                    <div class="mb-1 flex items-baseline gap-2">
                      <span class="text-[11px] uppercase tracking-wide text-slate-500">Winner</span>
                    </div>
                    <div
                      class={[
                        "flex min-h-6 min-w-0 items-center gap-1.5 rounded px-2 py-1 text-xs ring-1",
                        winnerSoftClass(row.best_variant_id),
                      ]}
                      title={`${row.best_family_label}: ${row.best_variant_label}`}
                    >
                      <span class={["h-2.5 w-2.5 shrink-0 rounded-full", winnerClass(row.best_variant_id)]}></span>
                      <span class="truncate font-semibold">{winnerShortLabel(row.best_variant_id)}</span>
                    </div>
                  </div>

                  <div>
                    <div class="mb-1 flex items-baseline justify-between gap-2">
                      <span class="text-[11px] uppercase tracking-wide text-slate-500">AIC gap</span>
                      <span class="font-mono text-xs text-slate-900">{fmt(row.delta_aic_to_next)}</span>
                    </div>
                    <div
                      class="h-2 rounded-full bg-white"
                      title={`Delta AIC to next candidate: ${fmt(row.delta_aic_to_next)}`}
                    >
                      <span
                        class={["block h-2 rounded-full", confidenceClass(row.confidence_label)]}
                        style={`width: ${aicWidth(row.delta_aic_to_next, maxDelta)}`}
                      ></span>
                    </div>
                  </div>

                  <div>
                    <div class="mb-1 flex items-baseline gap-2">
                      <span class="text-[11px] uppercase tracking-wide text-slate-500">Confidence</span>
                    </div>
                    <div class="grid grid-cols-4 gap-1">
                      {#each confidenceSteps as step (step)}
                        <span
                          class={[
                            "h-2 rounded-full",
                            row.confidence_label === step ? confidenceClass(step) : "bg-white",
                          ]}
                          title={labelForConfidence(step)}
                        ></span>
                      {/each}
                    </div>
                  </div>

                  <div>
                    <div class="mb-1 flex items-baseline justify-between gap-2">
                      <span class="text-[11px] uppercase tracking-wide text-slate-500">Candidates</span>
                      <span class="font-mono text-xs text-slate-900">{row.n_candidate_fits}</span>
                    </div>
                    <div class="flex gap-1" title={`${row.n_candidate_fits} candidate fit${row.n_candidate_fits === 1 ? "" : "s"}`}>
                      {#each candidatePips(row, maxCandidateCount) as pip (pip.index)}
                        <span
                          class={[
                            "h-2 flex-1 rounded-full",
                            pip.active ? "bg-slate-700" : "bg-white",
                          ]}
                        ></span>
                      {/each}
                    </div>
                  </div>

                  <div>
                    <div class="mb-1 flex items-baseline gap-2">
                      <span class="text-[11px] uppercase tracking-wide text-slate-500">Source</span>
                    </div>
                    <div
                      class={[
                        "flex min-h-6 items-center gap-1.5 rounded px-2 py-1 text-xs ring-1",
                        sourceSoftClass(row.source_data_level),
                      ]}
                      title={readable(row.source_data_level)}
                    >
                      <span class={["h-2.5 w-2.5 rounded-full", sourceClass(row.source_data_level)]}></span>
                      <span class="truncate font-semibold">{sourceShortLabel(row.source_data_level)}</span>
                    </div>
                  </div>

                  <div>
                    <div class="mb-1 flex items-baseline justify-between gap-2">
                      <span class="text-[11px] uppercase tracking-wide text-slate-500">Caveats</span>
                      <span class="font-mono text-xs text-slate-900">{caveatCount(row)}</span>
                    </div>
                    <div class="flex min-h-6 flex-wrap items-center gap-1">
                      {#if caveatCount(row) > 0}
                        {#each uniqueCaveatTags(row).slice(0, 3) as tag (tag)}
                          <span
                            class="inline-flex h-5 min-w-5 items-center justify-center rounded bg-warn-soft px-1 text-[10px] font-semibold text-warn"
                            title={caveatDefinitions[tag]?.description ?? labelForCaveat(tag)}
                          >
                            !
                          </span>
                        {/each}
                        {#if caveatCount(row) > 3}
                          <span class="font-mono text-[10px] text-warn">+{caveatCount(row) - 3}</span>
                        {/if}
                      {:else}
                        <span class="h-2 flex-1 rounded-full bg-white" title="no caveat tags"></span>
                      {/if}
                      {#if row.has_mixed_aic_scopes}
                        <span
                          class="inline-flex h-5 min-w-5 items-center justify-center rounded bg-amber-100 px-1 font-mono text-[10px] font-semibold text-amber-800"
                          title="mixed AIC comparison scopes"
                        >
                          M
                        </span>
                      {/if}
                    </div>
                  </div>
                </div>
              </div>

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
      <section class="rounded-md border border-slate-200 bg-white p-4" data-testid="family-verdicts">
        <h3 class="text-sm font-semibold text-slate-900">Family Verdicts</h3>
        <ul class="mt-3 space-y-3">
          {#each familyVerdicts as group (group.family)}
            <li>
              <div class="flex items-baseline justify-between gap-3">
                <p class="text-xs font-semibold text-slate-800">{group.family}</p>
                <span class="font-mono text-xs text-slate-500">{group.n}</span>
              </div>

              <div
                class="mt-2 flex h-2 overflow-hidden rounded-full bg-slate-100"
                title="winner family distribution"
              >
                {#each group.winnerSegments as segment (`${group.family}-${segment.key}`)}
                  <span
                    class={["h-2", winnerClass(segment.key)]}
                    style={`width: ${percent(segment.count, group.n)}`}
                    title={`${segment.label}: ${segment.count}`}
                  ></span>
                {/each}
              </div>

              <ul class="mt-2 flex flex-wrap gap-1">
                {#each group.winnerSegments.slice(0, 4) as segment (`${group.family}-${segment.key}-label`)}
                  <li
                    class={[
                      "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] ring-1",
                      winnerSoftClass(segment.key),
                    ]}
                  >
                    <span class={["h-1.5 w-1.5 rounded-full", winnerClass(segment.key)]}></span>
                    {segment.label} <span class="font-mono">{segment.count}</span>
                  </li>
                {/each}
              </ul>

              <div class="mt-2 grid grid-cols-3 gap-2">
                <div title={`${group.close} close model-selection rows`}>
                  <div class="mb-0.5 flex justify-between gap-1 text-[10px] text-slate-500">
                    <span>Close</span>
                    <span class="font-mono">{group.close}</span>
                  </div>
                  <div class="h-1.5 rounded-full bg-slate-100">
                    <span class="block h-1.5 rounded-full bg-amber-500" style={`width: ${percent(group.close, group.n)}`}></span>
                  </div>
                </div>
                <div title={`${group.caveats} caveated model-selection rows`}>
                  <div class="mb-0.5 flex justify-between gap-1 text-[10px] text-slate-500">
                    <span>Caveat</span>
                    <span class="font-mono">{group.caveats}</span>
                  </div>
                  <div class="h-1.5 rounded-full bg-slate-100">
                    <span class="block h-1.5 rounded-full bg-warn" style={`width: ${percent(group.caveats, group.n)}`}></span>
                  </div>
                </div>
                <div title={`${group.mixed} mixed-scope model-selection rows`}>
                  <div class="mb-0.5 flex justify-between gap-1 text-[10px] text-slate-500">
                    <span>Mixed</span>
                    <span class="font-mono">{group.mixed}</span>
                  </div>
                  <div class="h-1.5 rounded-full bg-slate-100">
                    <span class="block h-1.5 rounded-full bg-slate-600" style={`width: ${percent(group.mixed, group.n)}`}></span>
                  </div>
                </div>
              </div>
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
