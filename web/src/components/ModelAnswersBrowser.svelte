<script lang="ts">
  import FacetBar from "./FacetBar.svelte";
  import ConfidenceChip from "./ui/ConfidenceChip.svelte";

  // Progressive-fill ladder: how many of the 4 segments to fill for
  // each confidence level. Matches the dedicated ConfidenceChip
  // primitive so the header pill and the inline glyph strip read the
  // same way.
  const CONFIDENCE_FILLED: Record<string, number> = {
    decisive: 4,
    supported: 3,
    close: 2,
    single_candidate: 1,
  };

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

  function initialSingle(name: string): Set<string> {
    const value = initialParam(name);
    return value && value !== "all" ? new Set([value]) : new Set<string>();
  }

  const initialQuestion = initialParam("model_question") ?? "winners";
  const initialSort = initialParam("model_sort") ?? "delta-desc";

  let query = $state(initialParam("model_q") ?? "");
  let question = $state(questionLabels[initialQuestion] ? initialQuestion : "winners");
  let sortMode = $state(sortLabels[initialSort] ? initialSort : "delta-desc");
  let selected = $state<Record<string, Set<string>>>({
    task: initialSingle("model_family"),
    species: initialSingle("model_species"),
    curve: initialSingle("model_curve"),
    winner: initialSingle("model_winner"),
    confidence: initialSingle("model_confidence"),
  });

  function singlePick(key: string): string {
    return Array.from(selected[key] ?? new Set())[0] ?? "";
  }

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
      ((selected.task?.size ?? 0) > 0 ? 1 : 0) +
      ((selected.species?.size ?? 0) > 0 ? 1 : 0) +
      ((selected.curve?.size ?? 0) > 0 ? 1 : 0) +
      ((selected.winner?.size ?? 0) > 0 ? 1 : 0) +
      ((selected.confidence?.size ?? 0) > 0 ? 1 : 0),
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
    if (key === "ddm") return "bg-encoding-model-ddm";
    if (key === "click") return "bg-encoding-model-click";
    if (key === "sdt") return "bg-encoding-model-sdt";
    if (key === "chronometric") return "bg-encoding-model-chronometric";
    if (key === "logistic") return "bg-encoding-model-logistic";
    if (key === "rate") return "bg-encoding-model-bernoulli";
    if (key === "accuracy") return "bg-encoding-curve-hit-rate";
    return "bg-fg-muted";
  }

  function winnerSoftClass(keyOrVariant: string): string {
    const key = keyOrVariant.startsWith("model_variant.") ? winnerKey(keyOrVariant) : keyOrVariant;
    if (key === "ddm") return "bg-encoding-model-ddm-soft text-encoding-model-ddm-strong ring-encoding-model-ddm-edge";
    if (key === "click") return "bg-encoding-model-click-soft text-encoding-model-click-strong ring-encoding-model-click-edge";
    if (key === "sdt") return "bg-encoding-model-sdt-soft text-encoding-model-sdt-strong ring-encoding-model-sdt-edge";
    if (key === "chronometric") return "bg-encoding-model-chronometric-soft text-encoding-model-chronometric-strong ring-encoding-model-chronometric-edge";
    if (key === "logistic") return "bg-encoding-model-logistic-soft text-encoding-model-logistic-strong ring-encoding-model-logistic-edge";
    if (key === "rate") return "bg-encoding-model-bernoulli-soft text-encoding-model-bernoulli-strong ring-encoding-model-bernoulli-edge";
    if (key === "accuracy") return "bg-encoding-model-accuracy-soft text-encoding-model-accuracy-strong ring-encoding-model-accuracy-edge";
    return "bg-confidence-single-soft text-confidence-single-strong ring-confidence-single-edge";
  }

  function confidenceClass(label: string | undefined): string {
    if (label === "decisive") return "bg-confidence-decisive";
    if (label === "supported") return "bg-confidence-supported";
    if (label === "close") return "bg-confidence-close";
    if (label === "single_candidate") return "bg-confidence-single";
    return "bg-rule-strong";
  }

  function confidenceSoftClass(label: string | undefined): string {
    if (label === "decisive") return "bg-confidence-decisive-soft text-confidence-decisive-strong ring-confidence-decisive-edge";
    if (label === "supported") return "bg-confidence-supported-soft text-confidence-supported-strong ring-confidence-supported-edge";
    if (label === "close") return "bg-confidence-close-soft text-confidence-close-strong ring-confidence-close-edge";
    if (label === "single_candidate") return "bg-confidence-single-soft text-confidence-single-strong ring-confidence-single-edge";
    return "bg-confidence-single-soft text-confidence-single-strong ring-confidence-single-edge";
  }

  function sourceClass(level: string): string {
    if (level === "raw-trial") return "bg-encoding-source-raw";
    if (level === "processed-trial") return "bg-encoding-source-processed";
    if (level === "figure-source-data") return "bg-encoding-source-figure";
    return "bg-rule-strong";
  }

  function sourceShortLabel(level: string): string {
    if (level === "raw-trial") return "raw";
    if (level === "processed-trial") return "trials";
    if (level === "figure-source-data") return "figure";
    return "summary";
  }

  function sourceSoftClass(level: string): string {
    if (level === "raw-trial") return "bg-encoding-source-raw-soft text-encoding-source-raw-strong ring-encoding-source-raw-edge";
    if (level === "processed-trial") return "bg-encoding-source-processed-soft text-encoding-source-processed-strong ring-encoding-source-processed-edge";
    if (level === "figure-source-data") return "bg-encoding-source-figure-soft text-encoding-source-figure-strong ring-encoding-source-figure-edge";
    return "bg-confidence-single-soft text-confidence-single-strong ring-confidence-single-edge";
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

  // URL sync via $effect: re-run whenever any filter state changes.
  // replaceState skips adding history entries for filter tweaks.
  $effect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const setOrDelete = (name: string, value: string, defaultValue: string) => {
      if (value && value !== defaultValue) params.set(name, value);
      else params.delete(name);
    };
    setOrDelete("model_q", query.trim(), "");
    setOrDelete("model_question", question, "winners");
    setOrDelete("model_family", singlePick("task"), "");
    setOrDelete("model_species", singlePick("species"), "");
    setOrDelete("model_curve", singlePick("curve"), "");
    setOrDelete("model_winner", singlePick("winner"), "");
    setOrDelete("model_confidence", singlePick("confidence"), "");
    setOrDelete("model_sort", sortMode, "delta-desc");
    const search = params.toString();
    const next = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(null, "", next);
    }
  });

  function setSinglePick(key: string, value: string) {
    selected = {
      ...selected,
      [key]: value === "" ? new Set<string>() : new Set([value]),
    };
  }

  function clearAll() {
    query = "";
    question = "winners";
    sortMode = "delta-desc";
    selected = {
      task: new Set(),
      species: new Set(),
      curve: new Set(),
      winner: new Set(),
      confidence: new Set(),
    };
  }

  function applyPreset(value: string) {
    clearAll();
    if (value === "visual") setSinglePick("task", "Visual contrast discrimination");
    if (value === "rdm") setSinglePick("task", "Random-dot motion discrimination");
    if (value === "human") setSinglePick("species", "human");
    if (value === "mouse") setSinglePick("species", "mouse");
    if (value === "close") {
      question = "close";
      sortMode = "close-first";
    }
    if (value === "caveats") question = "caveats";
    if (value === "process") question = "process";
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
    const taskPick = singlePick("task");
    const speciesPick = singlePick("species");
    const curvePick = singlePick("curve");
    const winnerPick = singlePick("winner");
    const confidencePick = singlePick("confidence");
    const out = rows.filter((row) => {
      if (!hasQuestion(row)) return false;
      if (queryTokens.length > 0) {
        const text = haystack(row);
        if (!queryTokens.every((token) => text.includes(token))) return false;
      }
      if (taskPick && row.task_family !== taskPick) return false;
      if (speciesPick && row.species !== speciesPick) return false;
      if (curvePick && row.curve_type !== curvePick) return false;
      if (winnerPick && row.best_family_label !== winnerPick) return false;
      if (confidencePick && row.confidence_label !== confidencePick) return false;
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

  // FacetBar configuration
  const facets = $derived([
    {
      key: "task",
      label: "Task",
      mode: "single" as const,
      allLabel: "All tasks",
      options: taskOptions,
    },
    {
      key: "species",
      label: "Species",
      mode: "single" as const,
      allLabel: "All species",
      options: speciesOptions,
    },
    {
      key: "curve",
      label: "Curve",
      mode: "single" as const,
      allLabel: "All curves",
      options: curveOptions,
    },
    {
      key: "winner",
      label: "Winner",
      mode: "single" as const,
      allLabel: "All winners",
      options: winnerOptions,
    },
    {
      key: "confidence",
      label: "Confidence",
      mode: "single" as const,
      allLabel: "All labels",
      options: confidenceOptions.map((option) => ({
        ...option,
        label: labelForConfidence(option.value),
      })),
    },
  ]);

  const sortOptions = Object.entries(sortLabels).map(([value, label]) => ({
    value,
    label,
  }));

  const presets = [
    { key: "visual", label: "visual contrast" },
    { key: "rdm", label: "random-dot motion" },
    { key: "human", label: "human" },
    { key: "mouse", label: "mouse" },
    { key: "close", label: "close calls" },
    { key: "caveats", label: "source caveats" },
    { key: "process", label: "process models" },
  ];
</script>

<section class="space-y-4">
  <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
    <div class="rounded-md border border-rule bg-surface-raised p-3">
      <p class="text-xs uppercase tracking-wide text-fg-muted">Finding winners</p>
      <p class="mt-1 font-mono text-2xl font-semibold text-fg">{rows.length}</p>
      <p class="mt-1 text-xs text-fg-muted">{decisiveCount} decisive</p>
    </div>
    <div class="rounded-md border border-rule bg-surface-raised p-3">
      <p class="text-xs uppercase tracking-wide text-fg-muted">Close calls</p>
      <p class="mt-1 font-mono text-2xl font-semibold text-fg">{closeCount}</p>
      <p class="mt-1 text-xs text-fg-muted">low AIC separation</p>
    </div>
    <div class="rounded-md border border-rule bg-surface-raised p-3">
      <p class="text-xs uppercase tracking-wide text-fg-muted">Caveated rows</p>
      <p class="mt-1 font-mono text-2xl font-semibold text-fg">{caveatedRowCount}</p>
      <p class="mt-1 text-xs text-fg-muted">source or proxy caveats</p>
    </div>
    <div class="rounded-md border border-rule bg-surface-raised p-3">
      <p class="text-xs uppercase tracking-wide text-fg-muted">Process winners</p>
      <p class="mt-1 font-mono text-2xl font-semibold text-fg">{processCount}</p>
      <p class="mt-1 text-xs text-fg-muted">DDM, click, RT models</p>
    </div>
  </div>

  <div class="flex flex-wrap gap-2 text-body-xs">
    {#each Object.entries(questionLabels) as [value, label] (value)}
      <button
        type="button"
        class={[
          "rounded border px-2.5 py-1 font-semibold",
          question === value
            ? "border-accent bg-accent text-white"
            : "border-rule-strong bg-surface-raised text-fg-secondary hover:border-rule-emphasis hover:text-accent",
        ]}
        onclick={() => (question = value)}
      >
        {label}
      </button>
    {/each}
  </div>

  <FacetBar
    searchPlaceholder="paper, task, model, caveat"
    bind:query
    {sortOptions}
    bind:sortMode
    sortLabel="Sort"
    {presets}
    onPreset={applyPreset}
    {facets}
    bind:selected
    {activeFilterCount}
    onClearAll={clearAll}
  />

  <div class="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(17rem,0.65fr)]">
    <div class="space-y-3">
      <p class="text-sm text-fg-muted">
        Showing <span class="font-mono font-semibold text-fg">{filteredRows.length}</span>
        of <span class="font-mono text-fg">{rows.length}</span> finding-level winners.
      </p>

      <div
        class="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border border-rule bg-surface px-3 py-2 text-mono-id text-fg-muted"
        aria-label="Legend for caveat symbols on the cards below"
      >
        <span class="font-semibold text-fg-secondary">Legend:</span>
        <span class="inline-flex items-center gap-1.5">
          <span
            class="inline-flex h-5 min-w-5 items-center justify-center rounded bg-warn-soft px-1 text-[10px] font-semibold text-warn"
            aria-hidden="true"
          >!</span>
          <span>source or proxy caveat tag (hover for full description)</span>
        </span>
        <span class="inline-flex items-center gap-1.5">
          <span
            class="inline-flex h-5 min-w-5 items-center justify-center rounded bg-warn-soft px-1 font-mono text-mono-id font-semibold text-warn"
            aria-hidden="true"
          >M</span>
          <span>mixed AIC comparison scopes — the winner came from a different likelihood than the runners-up</span>
        </span>
        <span class="inline-flex items-center gap-1.5">
          <span aria-hidden="true">★</span>
          <span>winner row in the same-likelihood ranking</span>
        </span>
      </div>

      {#if filteredRows.length === 0}
        <section class="rounded-md border border-rule bg-surface-raised p-5 text-sm text-fg-muted">
          <p>No model-selection rows match the current filters.</p>
          {#if activeFilterCount > 0}
            <button type="button" class="mt-3 rounded border border-rule-strong bg-surface px-2 py-1 text-xs font-semibold text-fg hover:border-accent hover:text-accent" onclick={clearAll}>
              Clear filters
            </button>
          {/if}
        </section>
      {:else}
        <ul class="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {#each filteredRows.slice(0, 24) as row (row.selection_id)}
            <li class="rounded-md border border-rule bg-surface-raised p-4">
              <header class="flex min-w-0 items-start justify-between gap-3">
                <div class="min-w-0">
                  <h3 class="text-sm font-semibold leading-snug text-fg">
                    <a class="no-underline hover:text-accent" href={row.finding_href}>
                      {row.paper_label} · {row.stratification_label}
                    </a>
                  </h3>
                  <p class="mt-1 text-xs text-fg-muted">
                    {row.task_family} · {row.protocol_name}
                  </p>
                </div>
                <span
                  class={[
                    "shrink-0 rounded px-1.5 py-0.5 ring-1",
                    confidenceSoftClass(row.confidence_label),
                  ]}
                >
                  <ConfidenceChip
                    confidence={row.confidence_label}
                    delta={row.delta_aic_to_next}
                    showLabel={true}
                  />
                </span>
              </header>

              <div
                data-testid="model-glyph-strip"
                class="mt-3 rounded-md border border-rule bg-surface p-3"
                aria-label={`${row.paper_label} model-selection glyphs`}
              >
                <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div class="min-w-0">
                    <div class="mb-1 flex items-baseline gap-2">
                      <span class="text-[11px] uppercase tracking-wide text-fg-muted">Winner</span>
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
                      <span class="text-[11px] uppercase tracking-wide text-fg-muted">AIC gap</span>
                      <span class="font-mono text-xs text-fg">{fmt(row.delta_aic_to_next)}</span>
                    </div>
                    <div
                      class="h-2 rounded-full bg-surface-raised"
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
                      <span class="text-[11px] uppercase tracking-wide text-fg-muted">Confidence</span>
                    </div>
                    {#snippet confidenceSegments()}
                      {@const filled =
                        CONFIDENCE_FILLED[row.confidence_label ?? ""] ?? 0}
                      <div class="grid grid-cols-4 gap-1" title={labelForConfidence(row.confidence_label)}>
                        {#each [0, 1, 2, 3] as i (i)}
                          <span
                            class={[
                              "h-2 rounded-full",
                              i < filled
                                ? confidenceClass(row.confidence_label)
                                : "bg-surface-raised",
                            ]}
                          ></span>
                        {/each}
                      </div>
                    {/snippet}
                    {@render confidenceSegments()}
                  </div>

                  <div>
                    <div class="mb-1 flex items-baseline justify-between gap-2">
                      <span class="text-[11px] uppercase tracking-wide text-fg-muted">Candidates</span>
                      <span class="font-mono text-xs text-fg">{row.n_candidate_fits}</span>
                    </div>
                    <div class="flex gap-1" title={`${row.n_candidate_fits} candidate fit${row.n_candidate_fits === 1 ? "" : "s"}`}>
                      {#each candidatePips(row, maxCandidateCount) as pip (pip.index)}
                        <span
                          class={[
                            "h-2 flex-1 rounded-full",
                            pip.active ? "bg-fg-secondary" : "bg-surface-raised",
                          ]}
                        ></span>
                      {/each}
                    </div>
                  </div>

                  <div>
                    <div class="mb-1 flex items-baseline gap-2">
                      <span class="text-[11px] uppercase tracking-wide text-fg-muted">Source</span>
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
                      <span class="text-[11px] uppercase tracking-wide text-fg-muted">Caveats</span>
                      <span class="font-mono text-xs text-fg">{caveatCount(row)}</span>
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
                        <span class="h-2 flex-1 rounded-full bg-surface-raised" title="no caveat tags"></span>
                      {/if}
                      {#if row.has_mixed_aic_scopes}
                        <span
                          class="inline-flex h-5 min-w-5 items-center justify-center rounded bg-warn-soft px-1 font-mono text-mono-id font-semibold text-warn"
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
                  <dt class="text-fg-muted">Winner</dt>
                  <dd class="font-mono text-fg">{row.best_variant_label}</dd>
                </div>
                <div>
                  <dt class="text-fg-muted">Delta AIC</dt>
                  <dd class="font-mono text-fg">{fmt(row.delta_aic_to_next)}</dd>
                </div>
                <div>
                  <dt class="text-fg-muted">Scope</dt>
                  <dd class="text-fg-secondary">{labelForScope(row.comparison_scope)}</dd>
                </div>
                <div>
                  <dt class="text-fg-muted">Candidates</dt>
                  <dd class="font-mono text-fg">{row.n_candidate_fits}</dd>
                </div>
              </dl>

              <div class="mt-3 flex flex-wrap gap-1 text-[11px]">
                <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">{readable(row.species)}</span>
                <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">{readable(row.curve_type)}</span>
                <span class="rounded bg-surface-sunken px-2 py-0.5 text-fg-secondary">{readable(row.source_data_level)}</span>
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
                <span class="font-mono text-fg-muted">AIC {fmt(row.best_aic)}</span>
              </div>
            </li>
          {/each}
        </ul>
        {#if filteredRows.length > 24}
          <p class="text-xs text-fg-muted">Showing first 24 matching winners; use the detailed table below for the full filtered workflow.</p>
        {/if}
      {/if}
    </div>

    <aside class="space-y-4">
      <section class="rounded-md border border-rule bg-surface-raised p-4" data-testid="family-verdicts">
        <h3 class="text-sm font-semibold text-fg">Family Verdicts</h3>
        <ul class="mt-3 space-y-3">
          {#each familyVerdicts as group (group.family)}
            <li>
              <div class="flex items-baseline justify-between gap-3">
                <p class="text-xs font-semibold text-fg">{group.family}</p>
                <span class="font-mono text-xs text-fg-muted">{group.n}</span>
              </div>

              <div
                class="mt-2 flex h-2 overflow-hidden rounded-full bg-surface-sunken"
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
                  <div class="mb-0.5 flex justify-between gap-1 text-[10px] text-fg-muted">
                    <span>Close</span>
                    <span class="font-mono">{group.close}</span>
                  </div>
                  <div class="h-1.5 rounded-full bg-surface-sunken">
                    <span class="block h-1.5 rounded-full bg-encoding-coverage-protocol" style={`width: ${percent(group.close, group.n)}`}></span>
                  </div>
                </div>
                <div title={`${group.caveats} caveated model-selection rows`}>
                  <div class="mb-0.5 flex justify-between gap-1 text-[10px] text-fg-muted">
                    <span>Caveat</span>
                    <span class="font-mono">{group.caveats}</span>
                  </div>
                  <div class="h-1.5 rounded-full bg-surface-sunken">
                    <span class="block h-1.5 rounded-full bg-warn" style={`width: ${percent(group.caveats, group.n)}`}></span>
                  </div>
                </div>
                <div title={`${group.mixed} mixed-scope model-selection rows`}>
                  <div class="mb-0.5 flex justify-between gap-1 text-[10px] text-fg-muted">
                    <span>Mixed</span>
                    <span class="font-mono">{group.mixed}</span>
                  </div>
                  <div class="h-1.5 rounded-full bg-surface-sunken">
                    <span class="block h-1.5 rounded-full bg-fg-muted" style={`width: ${percent(group.mixed, group.n)}`}></span>
                  </div>
                </div>
              </div>
            </li>
          {/each}
        </ul>
      </section>

      <section class="rounded-md border border-rule bg-surface-raised p-4">
        <h3 class="text-sm font-semibold text-fg">Next Model Work</h3>
        <ul class="mt-3 space-y-3">
          {#each topRoadmapItems as item (item.rank)}
            <li>
              <div class="flex items-baseline justify-between gap-2">
                <p class="text-xs font-semibold text-fg">
                  {readable(item.issue_type)}
                </p>
                <span class="rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] uppercase text-fg-muted">
                  {item.priority_label}
                </span>
              </div>
              <p class="mt-1 break-all font-mono text-[10px] text-fg-muted">
                {item.target_id.replace("finding.", "").replace("slice.", "")}
              </p>
              {#if item.recommended_action}
                <p class="mt-1 line-clamp-2 text-[11px] text-fg-muted">
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
