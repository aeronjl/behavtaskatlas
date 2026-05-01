<script lang="ts">
  import type { FindingsIndex, FindingsEntry } from "../lib/findings";
  import { chartChrome, tones } from "../lib/encoding";

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

  const allEntries = $derived(data.findings as FindingsEntry[]);
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

  const defaultCurveType = allCurveTypes.includes("psychometric")
    ? "psychometric"
    : allCurveTypes[0] ?? "psychometric";

  let currentCurveType = $state(defaultCurveType);
  let active = $state<Record<FilterKey, Set<string>>>({
    species: new Set(filterOptions.species),
    source_data_level: new Set(filterOptions.source_data_level),
    evidence_type: new Set(filterOptions.evidence_type),
    response_modality: new Set(filterOptions.response_modality),
  });
  let yearStart = $state(minYear);
  let yearEnd = $state(maxYear);
  let searchText = $state("");

  // Trace level: how to collapse the 1 trace per finding wall.
  // - "aggregate" (default): one trace per (paper × condition). When a
  //   pooled finding exists in the group, use it; otherwise synthesise an
  //   n-weighted average across the per-subject findings.
  // - "pooled": only show findings with no subject_id (drops papers that
  //   only published per-subject curves).
  // - "all": every finding shown individually.
  type TraceMode = "aggregate" | "pooled" | "all";
  let traceMode = $state<TraceMode>("aggregate");
  const traceModeOptions: Array<{ key: TraceMode; label: string; description: string }> = [
    { key: "aggregate", label: "Per condition", description: "One trace per paper × condition. Subjects pooled where pooled curve doesn't exist." },
    { key: "all", label: "All curves", description: "Every finding shown individually." },
    { key: "pooled", label: "Pooled only", description: "Only published-pooled findings (drops per-subject)." },
  ];

  // ── Stimulus axis (x-label) selector ───────────────────────────────────────
  // Different psychometric findings calibrate the stimulus along incompatible
  // axes (signed motion coherence in % vs. signed click difference vs. signed
  // contrast). Plotting them on one axis is misleading, so the chart only
  // ever shows findings whose x_label matches the active selection. The
  // default is the most-populous group for the current curve type.

  type AxisOption = { label: string; units: string; count: number };

  const axisOptionsForCurve = $derived.by<AxisOption[]>(() => {
    const counts = new Map<string, AxisOption>();
    for (const entry of allEntries) {
      if (entry.curve_type !== currentCurveType) continue;
      const label = entry.x_label ?? "x";
      const units = entry.x_units ?? "";
      const key = `${label}|${units}`;
      const existing = counts.get(key);
      if (existing) existing.count += 1;
      else counts.set(key, { label, units, count: 1 });
    }
    return Array.from(counts.values()).sort((a, b) => b.count - a.count);
  });

  let activeXLabel = $state<string | null>(null);

  $effect(() => {
    // When curve type changes (or the available axes change because of
    // filters), pick the most populous group if the current pick is no
    // longer available.
    if (axisOptionsForCurve.length === 0) {
      activeXLabel = null;
      return;
    }
    if (
      !activeXLabel ||
      !axisOptionsForCurve.some((o) => o.label === activeXLabel)
    ) {
      activeXLabel = axisOptionsForCurve[0].label;
    }
  });

  // ── URL state sync ─────────────────────────────────────────────────────────
  // Filter state serialises to the query string so views are shareable.
  // Param keys are short: curve, species, level, evidence, response, years,
  // q, pooled, fit. A param is only emitted when the value diverges from the
  // page default; missing params imply defaults.

  const URL_PARAM_BY_FILTER: Record<FilterKey, string> = {
    species: "species",
    source_data_level: "level",
    evidence_type: "evidence",
    response_modality: "response",
  };

  let urlReady = $state(false);

  function applyUrlState() {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const curveParam = params.get("curve");
    if (curveParam && allCurveTypes.includes(curveParam)) {
      currentCurveType = curveParam;
    }
    const axisParam = params.get("axis");
    if (axisParam) activeXLabel = axisParam;
    const next = { ...active };
    let mutated = false;
    for (const [filterKey, paramKey] of Object.entries(URL_PARAM_BY_FILTER) as [FilterKey, string][]) {
      if (!params.has(paramKey)) continue;
      const raw = params.get(paramKey) ?? "";
      const requested = raw.split(",").map((v) => v.trim()).filter((v) => v.length > 0);
      const valid = filterOptions[filterKey];
      const filtered = requested.filter((v) => valid.includes(v));
      next[filterKey] = new Set(filtered);
      mutated = true;
    }
    if (mutated) active = next;
    const yearsParam = params.get("years");
    if (yearsParam) {
      const [aStr, bStr] = yearsParam.split("-");
      const a = Number(aStr);
      const b = Number(bStr);
      if (Number.isFinite(a)) yearStart = Math.max(minYear, Math.min(maxYear, a));
      if (Number.isFinite(b)) yearEnd = Math.max(minYear, Math.min(maxYear, b));
    }
    const q = params.get("q");
    if (q !== null) searchText = q;
    const modeParam = params.get("mode");
    if (modeParam === "all" || modeParam === "pooled" || modeParam === "aggregate") {
      traceMode = modeParam;
    } else if (params.get("pooled") === "1") {
      // Back-compat with pre-trace-mode shareable URLs.
      traceMode = "pooled";
    }
    if (params.get("fit") === "1") fitEnabled = true;
  }

  function setsEqual(a: Set<string>, b: string[]): boolean {
    if (a.size !== b.length) return false;
    for (const v of b) if (!a.has(v)) return false;
    return true;
  }

  function buildUrlState(): URLSearchParams {
    const params = new URLSearchParams();
    if (currentCurveType !== defaultCurveType) params.set("curve", currentCurveType);
    if (
      activeXLabel &&
      axisOptionsForCurve.length > 0 &&
      axisOptionsForCurve[0].label !== activeXLabel
    ) {
      params.set("axis", activeXLabel);
    }
    for (const [filterKey, paramKey] of Object.entries(URL_PARAM_BY_FILTER) as [FilterKey, string][]) {
      const set = active[filterKey];
      const allValues = filterOptions[filterKey];
      if (setsEqual(set, allValues)) continue;
      params.set(paramKey, Array.from(set).join(","));
    }
    if (yearStart !== minYear || yearEnd !== maxYear) {
      params.set("years", `${yearStart}-${yearEnd}`);
    }
    if (searchText.trim().length > 0) params.set("q", searchText.trim());
    if (traceMode !== "aggregate") params.set("mode", traceMode);
    if (fitEnabled) params.set("fit", "1");
    return params;
  }

  $effect(() => {
    if (typeof window === "undefined") return;
    if (!urlReady) {
      applyUrlState();
      urlReady = true;
      return;
    }
    const params = buildUrlState();
    const search = params.toString();
    const next = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(null, "", next);
    }
  });

  function isSubjectLevel(entry: FindingsEntry): boolean {
    return Boolean(entry.stratification?.subject_id);
  }

  const filteredEntries = $derived.by(() => {
    const needle = searchText.trim().toLowerCase();
    return allEntries.filter((entry) => {
      if (entry.curve_type !== currentCurveType) return false;
      if (activeXLabel && (entry.x_label ?? "x") !== activeXLabel) return false;
      if (traceMode === "pooled" && isSubjectLevel(entry)) return false;
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

  // displayEntries: the actual traces drawn on the chart. In aggregate
  // mode, each (paper × condition) group becomes ONE trace — the pooled
  // finding if available, otherwise an n-weighted average across the
  // per-subject findings in the group. Pooled and "all curves" modes pass
  // filteredEntries through unchanged.
  function aggregateGroup(group: FindingsEntry[]): FindingsEntry {
    const pooled = group.find((e) => !e.stratification?.subject_id);
    if (pooled) return pooled;
    const first = group[0];
    const xKeys = new Map<string, { x: number; ySum: number; nSum: number }>();
    for (const entry of group) {
      for (const p of entry.points) {
        const key = String(p.x);
        const acc = xKeys.get(key) ?? { x: p.x, ySum: 0, nSum: 0 };
        const weight = Math.max(p.n ?? 1, 1);
        acc.ySum += p.y * weight;
        acc.nSum += weight;
        xKeys.set(key, acc);
      }
    }
    const aggregatedPoints = Array.from(xKeys.values())
      .sort((a, b) => a.x - b.x)
      .map(({ x, ySum, nSum }) => ({
        x,
        y: nSum > 0 ? ySum / nSum : 0,
        n: nSum,
        y_lower: null,
        y_upper: null,
      }));
    const totalTrials = group.reduce(
      (sum, e) => sum + (typeof e.n_trials === "number" ? e.n_trials : 0),
      0,
    );
    const synthId = `${first.paper_id}|${first.stratification?.condition ?? ""}|aggregate`;
    return {
      ...first,
      finding_id: synthId,
      stratification: {
        condition: first.stratification?.condition ?? null,
        subject_id: null,
      },
      points: aggregatedPoints,
      n_trials: totalTrials,
      n_subjects: group.length,
    } as FindingsEntry;
  }

  const displayEntries = $derived.by<FindingsEntry[]>(() => {
    if (traceMode !== "aggregate") return filteredEntries;
    const groups = new Map<string, FindingsEntry[]>();
    for (const entry of filteredEntries) {
      const condition = entry.stratification?.condition ?? "";
      const key = `${entry.paper_id}|${condition}`;
      const list = groups.get(key) ?? [];
      list.push(entry);
      groups.set(key, list);
    }
    const out: FindingsEntry[] = [];
    for (const list of groups.values()) {
      out.push(aggregateGroup(list));
    }
    return out;
  });

  // Curve types whose y values are sample proportions (binary trial
  // outcomes). Wilson 95% CIs are well-defined when n is known; we
  // compute them at chart-time so static views show uncertainty even
  // when the upstream YAML didn't provide y_lower / y_upper.
  const BINARY_CURVE_TYPES = new Set([
    "psychometric",
    "accuracy_by_strength",
    "hit_rate",
    "yes_no_change_detection",
  ]);

  function wilsonInterval(p: number, n: number): { lower: number; upper: number } | null {
    if (!Number.isFinite(p) || !Number.isFinite(n) || n <= 0) return null;
    if (p < 0 || p > 1) return null;
    const z = 1.96;
    const z2 = z * z;
    const denom = n + z2;
    const center = (n * p + z2 / 2) / denom;
    const half = (z / denom) * Math.sqrt(n * p * (1 - p) + z2 / 4);
    return {
      lower: Math.max(0, center - half),
      upper: Math.min(1, center + half),
    };
  }

  const flatPoints = $derived.by(() =>
    displayEntries.flatMap((entry) =>
      entry.points.map((p) => {
        const authoredLower = (p as { y_lower?: number | null }).y_lower;
        const authoredUpper = (p as { y_upper?: number | null }).y_upper;
        let lower: number | null = null;
        let upper: number | null = null;
        if (
          authoredLower !== null &&
          authoredLower !== undefined &&
          authoredUpper !== null &&
          authoredUpper !== undefined
        ) {
          lower = authoredLower;
          upper = authoredUpper;
        } else if (BINARY_CURVE_TYPES.has(entry.curve_type)) {
          const ci = wilsonInterval(p.y, p.n);
          if (ci) {
            lower = ci.lower;
            upper = ci.upper;
          }
        }
        return {
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
          y_lower: lower,
          y_upper: upper,
        };
      })
    )
  );

  const flatBoundedPoints = $derived(
    flatPoints.filter((p) => p.y_lower !== null && p.y_upper !== null),
  );

  const yLabel = $derived.by(() => {
    if (displayEntries.length === 0) return "Y";
    return displayEntries[0].y_label;
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
    traceMode = "aggregate";
  }

  // ── View presets ───────────────────────────────────────────────────────────
  // Each preset resets to default first, then applies its overrides — clicking
  // a preset gives a fully-configured view rather than overlaying onto whatever
  // the user already had.

  type PresetKey =
    | "all"
    | "trial-backed"
    | "human"
    | "mouse"
    | "macaque"
    | "rdm"
    | "clicks"
    | "walsh-cue";

  const presets: Array<{ key: PresetKey; label: string; description: string }> = [
    {
      key: "all",
      label: "All",
      description: "All psychometric findings across the atlas.",
    },
    {
      key: "trial-backed",
      label: "Trial-backed",
      description: "Only findings sourced from raw or processed trial data.",
    },
    {
      key: "human",
      label: "Human",
      description: "Only human findings.",
    },
    {
      key: "mouse",
      label: "Mouse",
      description: "Only mouse findings.",
    },
    {
      key: "macaque",
      label: "Macaque",
      description: "Only macaque findings.",
    },
    {
      key: "rdm",
      label: "RDM cross-species",
      description: "Random-dot motion findings on signed motion coherence.",
    },
    {
      key: "clicks",
      label: "Clicks",
      description: "Auditory clicks task — rats and humans on the same axis.",
    },
    {
      key: "walsh-cue",
      label: "Walsh prior-cue",
      description: "Walsh 2024 prior-cue conditions on signed contrast.",
    },
  ];

  function intersect(allowed: string[], available: string[]): Set<string> {
    return new Set(allowed.filter((v) => available.includes(v)));
  }

  function applyPreset(key: PresetKey) {
    resetFilters();
    if (key === "all") return;
    if (key === "trial-backed") {
      active = {
        ...active,
        source_data_level: intersect(
          ["raw-trial", "processed-trial"],
          filterOptions.source_data_level,
        ),
      };
      return;
    }
    if (key === "human") {
      active = {
        ...active,
        species: intersect(["human"], filterOptions.species),
      };
      return;
    }
    if (key === "mouse") {
      active = {
        ...active,
        species: intersect(["mouse"], filterOptions.species),
      };
      return;
    }
    if (key === "macaque") {
      active = {
        ...active,
        species: intersect(["macaque"], filterOptions.species),
      };
      return;
    }
    if (key === "rdm") {
      searchText = "motion";
      const rdmAxis = axisOptionsForCurve.find((o) =>
        o.label.toLowerCase().includes("motion coherence"),
      );
      if (rdmAxis) activeXLabel = rdmAxis.label;
      return;
    }
    if (key === "clicks") {
      searchText = "click";
      const clicksAxis = axisOptionsForCurve.find((o) =>
        o.label.toLowerCase().includes("click"),
      );
      if (clicksAxis) activeXLabel = clicksAxis.label;
      return;
    }
    if (key === "walsh-cue") {
      searchText = "walsh";
      const walshAxis = axisOptionsForCurve.find((o) =>
        o.label.toLowerCase().includes("contrast"),
      );
      if (walshAxis) activeXLabel = walshAxis.label;
      return;
    }
  }

  // Filters start collapsed on every screen size — progressive disclosure.
  // Presets cover the common combos; Refine opens the full checkbox panel.
  let filtersExpanded = $state(false);

  // Copy-link affordance — relies on the URL-sync effect to keep the URL
  // up to date with current filter state.
  let copyState = $state<"idle" | "copied" | "error">("idle");

  async function copyLink() {
    if (typeof window === "undefined") return;
    const href = window.location.href;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(href);
      } else {
        const ta = document.createElement("textarea");
        ta.value = href;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      copyState = "copied";
      setTimeout(() => {
        copyState = "idle";
      }, 1500);
    } catch (err) {
      console.error(err);
      copyState = "error";
      setTimeout(() => {
        copyState = "idle";
      }, 1500);
    }
  }

  // ── Pinned views ────────────────────────────────────────────────────────
  // The user already gets shareable URLs via the URL-sync effect; pinned
  // views are the personal-bookmark companion. Each pin captures the
  // current search portion of the URL plus a derived label (curve type,
  // active filters) and persists in localStorage so the user's tray
  // survives reloads and follows their browser. No server.

  type PinnedView = {
    id: string;
    name: string;
    search: string; // URL search part, e.g. "?curve=accuracy_by_strength&species=mouse"
    curveType: string;
    filterCount: number;
    savedAt: number;
  };

  const PINNED_KEY = "behavtaskatlas:pinnedViews:findings";
  let pinnedViews = $state<PinnedView[]>([]);

  $effect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(PINNED_KEY);
      if (raw) pinnedViews = JSON.parse(raw) as PinnedView[];
    } catch (err) {
      console.error("Failed to read pinned views", err);
    }
  });

  function persistPinned(next: PinnedView[]) {
    pinnedViews = next;
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(PINNED_KEY, JSON.stringify(next));
    } catch (err) {
      console.error("Failed to persist pinned views", err);
    }
  }

  // Derive a display name from current filter state. Prefers an active
  // preset's label; falls back to the curve type plus a short "X filters"
  // tag so the pinned-views tray reads like a list of meaningful queries
  // rather than a wall of UUIDs.
  function deriveViewName(): string {
    for (const preset of presets) {
      if (isPresetActive(preset.key)) {
        return preset.key === "all"
          ? `${currentCurveType.replace(/_/g, " ")} · all`
          : `${currentCurveType.replace(/_/g, " ")} · ${preset.label}`;
      }
    }
    const parts: string[] = [currentCurveType.replace(/_/g, " ")];
    if (active.species.size === 1) parts.push(Array.from(active.species)[0]);
    else if (active.species.size < filterOptions.species.length)
      parts.push(`${active.species.size} species`);
    if (
      active.source_data_level.size <
      filterOptions.source_data_level.length
    ) {
      parts.push(`${active.source_data_level.size} source levels`);
    }
    if (searchText.trim().length > 0) parts.push(`"${searchText.trim()}"`);
    if (parts.length === 1) parts.push("default");
    return parts.join(" · ");
  }

  function pinCurrentView() {
    if (typeof window === "undefined") return;
    const search = buildUrlState().toString();
    const view: PinnedView = {
      id: `view-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: deriveViewName(),
      search,
      curveType: currentCurveType,
      filterCount: activeFilterCount,
      savedAt: Date.now(),
    };
    // Avoid duplicates: if a pin already matches the same search string,
    // refresh its savedAt timestamp instead of stacking another row.
    const existing = pinnedViews.find((v) => v.search === search);
    if (existing) {
      persistPinned(
        pinnedViews.map((v) =>
          v.id === existing.id ? { ...v, savedAt: Date.now(), name: view.name } : v,
        ),
      );
      return;
    }
    persistPinned([view, ...pinnedViews].slice(0, 12));
  }

  function removePinnedView(id: string) {
    persistPinned(pinnedViews.filter((v) => v.id !== id));
  }

  function loadPinnedView(view: PinnedView) {
    if (typeof window === "undefined") return;
    const search = view.search.length > 0 ? `?${view.search}` : "";
    window.location.href = `${window.location.pathname}${search}`;
  }

  const isCurrentViewPinned = $derived.by(() => {
    if (typeof window === "undefined") return false;
    const search = buildUrlState().toString();
    return pinnedViews.some((v) => v.search === search);
  });

  const filteredSummary = $derived.by(() => {
    const papers = new Set<string>();
    const species = new Set<string>();
    for (const entry of filteredEntries) {
      papers.add(entry.paper_id);
      if (entry.species) species.add(entry.species);
    }
    return {
      papers: papers.size,
      species: species.size,
    };
  });

  const activeFilterCount = $derived.by(() => {
    let n = 0;
    if (active.species.size !== filterOptions.species.length) n += 1;
    if (active.source_data_level.size !== filterOptions.source_data_level.length) n += 1;
    if (active.evidence_type.size !== filterOptions.evidence_type.length) n += 1;
    if (active.response_modality.size !== filterOptions.response_modality.length) n += 1;
    if (yearStart !== minYear || yearEnd !== maxYear) n += 1;
    if (searchText.trim().length > 0) n += 1;
    if (traceMode !== "aggregate") n += 1;
    return n;
  });

  // ── Empty-state suggestions ────────────────────────────────────────────
  // When the current filter combination yields no findings, compute
  // which single relaxation would unlock the most. Lets the empty
  // state offer "Drop the X filter to see Y more findings" instead of
  // a dead end.

  type RelaxKey =
    | "species"
    | "source_data_level"
    | "evidence_type"
    | "response_modality"
    | "year"
    | "search"
    | "trace_mode";

  const RELAX_LABELS: Record<RelaxKey, string> = {
    species: "species",
    source_data_level: "source level",
    evidence_type: "evidence type",
    response_modality: "response modality",
    year: "year range",
    search: "search text",
    trace_mode: "trace mode",
  };

  function entryMatchesExcept(entry: FindingsEntry, skip: RelaxKey | null): boolean {
    if (entry.curve_type !== currentCurveType) return false;
    if (activeXLabel && (entry.x_label ?? "x") !== activeXLabel) return false;
    if (skip !== "trace_mode" && traceMode === "pooled" && isSubjectLevel(entry))
      return false;
    if (
      skip !== "species" &&
      entry.species &&
      !active.species.has(entry.species)
    )
      return false;
    if (
      skip !== "source_data_level" &&
      entry.source_data_level &&
      !active.source_data_level.has(entry.source_data_level)
    )
      return false;
    if (
      skip !== "evidence_type" &&
      entry.evidence_type &&
      !active.evidence_type.has(entry.evidence_type)
    )
      return false;
    if (
      skip !== "response_modality" &&
      entry.response_modality &&
      !active.response_modality.has(entry.response_modality)
    )
      return false;
    if (skip !== "year" && (entry.paper_year < yearStart || entry.paper_year > yearEnd))
      return false;
    if (skip !== "search") {
      const needle = searchText.trim().toLowerCase();
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
    }
    return true;
  }

  type Relaxation = { key: RelaxKey; label: string; count: number };

  const relaxationSuggestions = $derived.by<Relaxation[]>(() => {
    if (filteredEntries.length > 0) return [];
    const candidates: Array<{ key: RelaxKey; active: boolean }> = [
      { key: "species", active: active.species.size !== filterOptions.species.length },
      { key: "source_data_level", active: active.source_data_level.size !== filterOptions.source_data_level.length },
      { key: "evidence_type", active: active.evidence_type.size !== filterOptions.evidence_type.length },
      { key: "response_modality", active: active.response_modality.size !== filterOptions.response_modality.length },
      { key: "year", active: yearStart !== minYear || yearEnd !== maxYear },
      { key: "search", active: searchText.trim().length > 0 },
      { key: "trace_mode", active: traceMode !== "aggregate" },
    ];
    const out: Relaxation[] = [];
    for (const cand of candidates) {
      if (!cand.active) continue;
      const count = allEntries.reduce(
        (acc, entry) => (entryMatchesExcept(entry, cand.key) ? acc + 1 : acc),
        0,
      );
      if (count > 0) {
        out.push({ key: cand.key, label: RELAX_LABELS[cand.key], count });
      }
    }
    return out.sort((a, b) => b.count - a.count).slice(0, 3);
  });

  function relaxFilter(key: RelaxKey) {
    if (key === "species") active = { ...active, species: new Set(filterOptions.species) };
    else if (key === "source_data_level")
      active = { ...active, source_data_level: new Set(filterOptions.source_data_level) };
    else if (key === "evidence_type")
      active = { ...active, evidence_type: new Set(filterOptions.evidence_type) };
    else if (key === "response_modality")
      active = { ...active, response_modality: new Set(filterOptions.response_modality) };
    else if (key === "year") {
      yearStart = minYear;
      yearEnd = maxYear;
    } else if (key === "search") searchText = "";
    else if (key === "trace_mode") traceMode = "aggregate";
  }

  function isPresetActive(key: PresetKey): boolean {
    const hasFullSet = (filterKey: FilterKey) =>
      active[filterKey].size === filterOptions[filterKey].length;
    const allDefault =
      hasFullSet("species") &&
      hasFullSet("source_data_level") &&
      hasFullSet("evidence_type") &&
      hasFullSet("response_modality") &&
      yearStart === minYear &&
      yearEnd === maxYear &&
      searchText === "" &&
      traceMode === "aggregate";
    if (key === "all") return allDefault;
    if (key === "trial-backed") {
      return (
        hasFullSet("species") &&
        hasFullSet("evidence_type") &&
        hasFullSet("response_modality") &&
        active.source_data_level.size <= 2 &&
        Array.from(active.source_data_level).every((v) =>
          ["raw-trial", "processed-trial"].includes(v),
        ) &&
        searchText === ""
      );
    }
    if (key === "human" || key === "mouse" || key === "macaque") {
      return (
        active.species.size === 1 &&
        active.species.has(key) &&
        hasFullSet("source_data_level") &&
        searchText === ""
      );
    }
    if (key === "rdm") return searchText === "motion";
    if (key === "clicks") return searchText === "click";
    if (key === "walsh-cue") return searchText === "walsh";
    return false;
  }

  let chartContainer: HTMLDivElement | undefined = $state();
  let disagreementContainer: HTMLDivElement | undefined = $state();
  let chartReady = $state(false);
  let vegaEmbed: any = null;
  let chartView: any = null;
  let disagreementView: any = null;

  $effect(() => {
    if (!chartContainer || vegaEmbed) return;
    (async () => {
      const mod = await import("vega-embed");
      vegaEmbed = mod.default ?? mod;
      chartReady = true;
    })();
  });

  // ── In-browser fitting via Pyodide + scipy ─────────────────────────────────

  type FitStatus =
    | "idle"
    | "loading-runtime"
    | "loading-packages"
    | "fitting"
    | "done"
    | "error";

  let fitEnabled = $state(false);
  let fitStatus = $state<FitStatus>("idle");
  let fitError = $state("");
  type FitParams = {
    mu: number;
    sigma: number;
    gamma: number;
    lapse: number;
  };
  type PerCurveFit = {
    finding_id: string;
    line: Array<{ x: number; y: number }>;
    params: FitParams | null;
    threshold: number | null;
    threshold_target_y: number;
  };
  type DisagreementPoint = {
    x: number;
    std: number;
    min: number;
    max: number;
    n_curves: number;
  };
  type SelectionRanking = {
    variant: string;
    label: string;
    n_params: number;
    params: Record<string, number>;
    log_likelihood: number;
    aic: number;
    delta_aic: number;
  };
  let fitData = $state<{
    perCurve: PerCurveFit[];
    pooled: { line: Array<{ x: number; y: number }>; ci_band: Array<{ x: number; y: number; lower: number; upper: number }> | null; params: FitParams } | null;
    disagreement: DisagreementPoint[];
    selectionRanking: SelectionRanking[];
    curveType: string;
    filterSignature: string;
    targetY: number;
  } | null>(null);

  let pyodideRuntime: any = null;
  let pyodideRuntimePromise: Promise<any> | null = null;

  const PYODIDE_VERSION = "0.26.4";
  const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

  const FIT_PYTHON = `
import json as _fit_json
import numpy as np
from scipy import optimize


def _logistic4(x, mu, sigma, gamma, lapse):
    sig = max(float(sigma), 1e-6)
    return gamma + (1 - gamma - lapse) / (1 + np.exp(-(x - mu) / sig))


def _fit_one(points, force_lower=None):
    if len(points) < 4:
        return None
    xs = np.array([p["x"] for p in points], dtype=float)
    ys = np.array([p["y"] for p in points], dtype=float)
    ns = np.array([max(p.get("n", 1), 1) for p in points], dtype=float)
    sigma_weight = 1.0 / np.sqrt(ns)
    mu0 = float(np.mean(xs))
    span = float(np.max(xs) - np.min(xs)) or 1.0
    sigma0 = max(span / 4.0, 1e-3)
    try:
        if force_lower is not None:
            def _model(x, mu, sigma, lapse):
                return _logistic4(x, mu, sigma, force_lower, lapse)
            popt, _ = optimize.curve_fit(
                _model, xs, ys, p0=[mu0, sigma0, 0.05],
                sigma=sigma_weight, absolute_sigma=False,
                bounds=([-np.inf, 1e-3, 0.0], [np.inf, np.inf, 0.49]),
                maxfev=4000,
            )
            mu, sigma, lapse = popt
            return {
                "mu": float(mu),
                "sigma": float(sigma),
                "gamma": float(force_lower),
                "lapse": float(lapse),
            }
        popt, _ = optimize.curve_fit(
            _logistic4, xs, ys,
            p0=[mu0, sigma0, 0.05, 0.05],
            sigma=sigma_weight, absolute_sigma=False,
            bounds=([-np.inf, 1e-3, 0.0, 0.0], [np.inf, np.inf, 0.49, 0.49]),
            maxfev=4000,
        )
        mu, sigma, gamma, lapse = popt
        return {
            "mu": float(mu),
            "sigma": float(sigma),
            "gamma": float(gamma),
            "lapse": float(lapse),
        }
    except Exception:
        return None


def _smooth(params, x_min, x_max, n=80, force_lower=None):
    xs = np.linspace(x_min, x_max, n)
    gamma = force_lower if force_lower is not None else params["gamma"]
    ys = _logistic4(xs, params["mu"], params["sigma"], gamma, params["lapse"])
    return [
        {"x": float(x), "y": float(y)}
        for x, y in zip(xs.tolist(), ys.tolist())
    ]


def _threshold_at(params, target_y, force_lower=None):
    """Solve y(x) = target_y for x. Returns None if the target lies
    outside the asymptotes."""
    gamma = force_lower if force_lower is not None else params["gamma"]
    lapse = params["lapse"]
    span = 1.0 - gamma - lapse
    if span <= 0:
        return None
    z = (target_y - gamma) / span
    if z <= 0 or z >= 1:
        return None
    sig = max(float(params["sigma"]), 1e-6)
    return float(params["mu"] - sig * np.log((1.0 - z) / z))


def _bernoulli_loglik(points, predictor):
    """Aggregated Bernoulli log-likelihood for a vector of (y, n) per
    x. Used to AIC-rank model variants on the pooled curve."""
    eps = 1e-10
    ll = 0.0
    for p in points:
        n = max(p.get("n", 1), 1)
        y = float(p["y"])
        p_hat = float(predictor(p["x"]))
        p_hat = max(min(p_hat, 1 - eps), eps)
        ll += n * (y * np.log(p_hat) + (1 - y) * np.log(1 - p_hat))
    return float(ll)


def _rank_variants(points):
    """Fit four nested logistic / null variants on the same pooled data
    and AIC-rank them. Returns a list ordered by AIC ascending; each
    item has variant id, free-parameter count, fitted parameters,
    log-likelihood, and AIC. The ranking is the in-browser analogue of
    the build-time AIC selection on /models."""
    if not points:
        return []
    xs = np.array([p["x"] for p in points], dtype=float)
    ys = np.array([p["y"] for p in points], dtype=float)
    ns = np.array([max(p.get("n", 1), 1) for p in points], dtype=float)
    if len(xs) < 4:
        return []
    sigma_weight = 1.0 / np.sqrt(ns)
    mu0 = float(np.mean(xs))
    span = float(np.max(xs) - np.min(xs)) or 1.0
    sigma0 = max(span / 4.0, 1e-3)
    eps = 1e-10

    results = []

    # 1. Bernoulli rate (null): single p across all data, no x dependence.
    p_rate = float(np.average(ys, weights=ns))
    p_rate_clipped = max(min(p_rate, 1 - eps), eps)
    rate_predictor = lambda _x, p=p_rate_clipped: p
    rate_ll = _bernoulli_loglik(points, rate_predictor)
    results.append({
        "variant": "bernoulli-rate",
        "label": "Constant rate",
        "n_params": 1,
        "params": {"p": p_rate},
        "log_likelihood": rate_ll,
        "aic": 2 * 1 - 2 * rate_ll,
    })

    # 2. Logistic-2param: mu, sigma; lapse and gamma pinned at 0.
    try:
        def _model2(x, mu, sigma):
            return _logistic4(x, mu, sigma, 0.0, 0.0)
        popt2, _ = optimize.curve_fit(
            _model2, xs, ys, p0=[mu0, sigma0],
            sigma=sigma_weight, absolute_sigma=False,
            bounds=([-np.inf, 1e-3], [np.inf, np.inf]),
            maxfev=4000,
        )
        mu, sigma = popt2
        params = {"mu": float(mu), "sigma": float(sigma), "gamma": 0.0, "lapse": 0.0}
        predictor = lambda x, p=params: _logistic4(np.array([x]), p["mu"], p["sigma"], 0.0, 0.0)[0]
        ll = _bernoulli_loglik(points, predictor)
        results.append({
            "variant": "logistic-2param",
            "label": "Logistic μ, σ",
            "n_params": 2,
            "params": params,
            "log_likelihood": ll,
            "aic": 2 * 2 - 2 * ll,
        })
    except Exception:
        pass

    # 3. Logistic-3param: mu, sigma, symmetric lapse (gamma = lapse).
    try:
        def _model3(x, mu, sigma, lapse):
            return _logistic4(x, mu, sigma, lapse, lapse)
        popt3, _ = optimize.curve_fit(
            _model3, xs, ys, p0=[mu0, sigma0, 0.05],
            sigma=sigma_weight, absolute_sigma=False,
            bounds=([-np.inf, 1e-3, 0.0], [np.inf, np.inf, 0.49]),
            maxfev=4000,
        )
        mu, sigma, lapse = popt3
        params = {"mu": float(mu), "sigma": float(sigma), "gamma": float(lapse), "lapse": float(lapse)}
        predictor = lambda x, p=params: _logistic4(np.array([x]), p["mu"], p["sigma"], p["gamma"], p["lapse"])[0]
        ll = _bernoulli_loglik(points, predictor)
        results.append({
            "variant": "logistic-3param-symmetric",
            "label": "Logistic μ, σ, symmetric lapse",
            "n_params": 3,
            "params": params,
            "log_likelihood": ll,
            "aic": 2 * 3 - 2 * ll,
        })
    except Exception:
        pass

    # 4. Logistic-4param: full mu, sigma, gamma, lapse.
    full = _fit_one(points)
    if full is not None:
        predictor = lambda x, p=full: _logistic4(np.array([x]), p["mu"], p["sigma"], p["gamma"], p["lapse"])[0]
        ll = _bernoulli_loglik(points, predictor)
        results.append({
            "variant": "logistic-4param",
            "label": "Logistic μ, σ, γ, λ",
            "n_params": 4,
            "params": full,
            "log_likelihood": ll,
            "aic": 2 * 4 - 2 * ll,
        })

    results.sort(key=lambda r: r["aic"])
    if results:
        best = results[0]["aic"]
        for r in results:
            r["delta_aic"] = float(r["aic"] - best)
    return results


def fit_curves(payload_json):
    payload = _fit_json.loads(payload_json)
    curves = payload["curves"]
    pin_lower = payload.get("pin_lower")
    n_boot = int(payload.get("n_bootstrap", 80))

    per_curve = []
    all_points = []
    target_y = float(payload.get("threshold_target", 0.75))
    for c in curves:
        params = _fit_one(c["points"], force_lower=pin_lower)
        if c["points"]:
            xs = [p["x"] for p in c["points"]]
            x_min = min(xs)
            x_max = max(xs)
            line = (
                _smooth(params, x_min, x_max, force_lower=pin_lower)
                if params else []
            )
        else:
            line = []
        threshold = (
            _threshold_at(params, target_y, force_lower=pin_lower)
            if params else None
        )
        per_curve.append({
            "finding_id": c["finding_id"],
            "params": params,
            "line": line,
            "threshold": threshold,
            "threshold_target_y": target_y,
        })
        all_points.extend(c["points"])

    pooled = None
    if all_points and len(curves) >= 1:
        pooled_params = _fit_one(all_points, force_lower=pin_lower)
        if pooled_params is not None:
            xs_all = [p["x"] for p in all_points]
            x_min = min(xs_all)
            x_max = max(xs_all)
            line = _smooth(pooled_params, x_min, x_max, force_lower=pin_lower)
            ci_band = None
            if len(curves) >= 2 and n_boot > 0:
                rng = np.random.default_rng(42)
                boot_lines = []
                for _ in range(n_boot):
                    idx = rng.integers(0, len(curves), size=len(curves))
                    resampled = []
                    for i in idx:
                        resampled.extend(curves[int(i)]["points"])
                    pb = _fit_one(resampled, force_lower=pin_lower)
                    if pb is None:
                        continue
                    boot_lines.append([
                        p["y"] for p in _smooth(pb, x_min, x_max, force_lower=pin_lower)
                    ])
                if boot_lines:
                    arr = np.array(boot_lines)
                    lower = np.percentile(arr, 2.5, axis=0)
                    upper = np.percentile(arr, 97.5, axis=0)
                    ci_band = [
                        {
                            "x": p["x"],
                            "y": p["y"],
                            "lower": float(lo),
                            "upper": float(up),
                        }
                        for p, lo, up in zip(line, lower.tolist(), upper.tolist())
                    ]
            pooled = {
                "params": pooled_params,
                "line": line,
                "ci_band": ci_band,
            }

    disagreement = []
    if pooled is not None:
        valid = [c for c in per_curve if c["params"] is not None]
        if len(valid) >= 2:
            pooled_xs = [p["x"] for p in pooled["line"]]
            for x in pooled_xs:
                ys = []
                for c in valid:
                    p = c["params"]
                    gamma = pin_lower if pin_lower is not None else p["gamma"]
                    ys.append(
                        float(_logistic4(
                            np.array([x]),
                            p["mu"], p["sigma"], gamma, p["lapse"],
                        )[0])
                    )
                arr = np.array(ys)
                disagreement.append({
                    "x": x,
                    "std": float(np.std(arr, ddof=1)),
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "n_curves": len(ys),
                })

    selection_ranking = []
    if pin_lower is None and all_points:
        try:
            selection_ranking = _rank_variants(all_points)
        except Exception:
            selection_ranking = []

    return _fit_json.dumps({
        "per_curve": per_curve,
        "pooled": pooled,
        "disagreement": disagreement,
        "selection_ranking": selection_ranking,
    })
`;

  async function ensureFitRuntime(): Promise<any> {
    if (pyodideRuntime) return pyodideRuntime;
    if (pyodideRuntimePromise) return pyodideRuntimePromise;
    fitStatus = "loading-runtime";
    pyodideRuntimePromise = (async () => {
      const scriptId = "pyodide-cdn-script";
      if (typeof document !== "undefined" && !document.getElementById(scriptId)) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement("script");
          script.id = scriptId;
          script.src = `${PYODIDE_BASE}pyodide.js`;
          script.async = true;
          script.onload = () => resolve();
          script.onerror = () =>
            reject(new Error("Failed to load Pyodide script"));
          document.head.appendChild(script);
        });
      }
      const w: any = window;
      const py = await w.loadPyodide({ indexURL: PYODIDE_BASE });
      fitStatus = "loading-packages";
      await py.loadPackage(["numpy", "scipy"]);
      await py.runPythonAsync(FIT_PYTHON);
      pyodideRuntime = py;
      return py;
    })();
    return pyodideRuntimePromise;
  }

  function pinLowerFor(curveType: string): number | null {
    if (curveType === "accuracy_by_strength") return 0.5;
    return null;
  }

  // Signature of the current selection; the effect re-runs the fit when it
  // changes while fitEnabled is true.
  const signature = $derived(
    JSON.stringify({
      curveType: currentCurveType,
      ids: displayEntries.map((e) => e.finding_id),
    }),
  );

  async function runFit() {
    fitError = "";
    if (displayEntries.length === 0) {
      fitData = null;
      fitStatus = "done";
      return;
    }
    try {
      const py = await ensureFitRuntime();
      fitStatus = "fitting";
      const curves = displayEntries.map((entry) => ({
        finding_id: entry.finding_id,
        points: entry.points.map((p) => ({ x: p.x, y: p.y, n: p.n })),
      }));
      const targetY =
        currentCurveType === "psychometric"
          ? 0.75
          : currentCurveType === "accuracy_by_strength"
            ? 0.84
            : 0.75;
      const payload = JSON.stringify({
        curves,
        pin_lower: pinLowerFor(currentCurveType),
        n_bootstrap: 80,
        threshold_target: targetY,
      });
      py.globals.set("_fit_payload", payload);
      const result: any = await py.runPythonAsync("fit_curves(_fit_payload)");
      const json = String(result ?? "{}");
      result?.destroy?.();
      const parsed = JSON.parse(json);
      fitData = {
        perCurve: parsed.per_curve ?? [],
        pooled: parsed.pooled ?? null,
        disagreement: parsed.disagreement ?? [],
        selectionRanking: parsed.selection_ranking ?? [],
        curveType: currentCurveType,
        filterSignature: signature,
        targetY,
      };
      fitStatus = "done";
    } catch (err) {
      fitError = err instanceof Error ? err.message : String(err);
      fitStatus = "error";
    }
  }

  // Recompute fit when filters change while fitting is enabled.
  $effect(() => {
    if (!fitEnabled) {
      if (fitStatus !== "idle") fitStatus = "idle";
      return;
    }
    if (fitData?.filterSignature === signature && fitStatus === "done") return;
    runFit();
  });

  const FIT_LINE_VALUES = $derived.by(() => {
    if (!fitEnabled || !fitData || fitData.curveType !== currentCurveType) {
      return [];
    }
    return fitData.perCurve.flatMap((c) =>
      c.line.map((p) => ({
        finding_id: c.finding_id,
        paper_citation:
          displayEntries.find((e) => e.finding_id === c.finding_id)?.paper_citation
          ?? c.finding_id,
        x: p.x,
        y: p.y,
      })),
    );
  });

  const POOLED_LINE_VALUES = $derived.by(() => {
    if (!fitEnabled || !fitData?.pooled) return [];
    return fitData.pooled.line.map((p) => ({ x: p.x, y: p.y }));
  });

  const POOLED_BAND_VALUES = $derived.by(() => {
    if (!fitEnabled || !fitData?.pooled?.ci_band) return [];
    return fitData.pooled.ci_band.map((p) => ({
      x: p.x,
      lower: p.lower,
      upper: p.upper,
    }));
  });

  const DISAGREEMENT_VALUES = $derived.by(() => {
    if (!fitEnabled || !fitData?.disagreement) return [];
    return fitData.disagreement;
  });

  type FitRow = {
    finding_id: string;
    paper_citation: string;
    paper_year: number;
    species: string | null;
    n_trials: number | null;
    mu: number | null;
    sigma: number | null;
    threshold: number | null;
    gamma: number | null;
    lapse: number | null;
  };

  type SortColumn =
    | "paper_year"
    | "paper_citation"
    | "n_trials"
    | "mu"
    | "sigma"
    | "threshold"
    | "lapse";
  let sortColumn = $state<SortColumn>("sigma");
  let sortDir = $state<"asc" | "desc">("asc");

  function setSort(col: SortColumn) {
    if (sortColumn === col) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortColumn = col;
      sortDir = col === "paper_year" ? "desc" : "asc";
    }
  }

  const fitRows = $derived.by<FitRow[]>(() => {
    if (!fitEnabled || !fitData) return [];
    if (fitData.curveType !== currentCurveType) return [];
    const rows: FitRow[] = fitData.perCurve.map((c) => {
      const entry = displayEntries.find((e) => e.finding_id === c.finding_id);
      return {
        finding_id: c.finding_id,
        paper_citation: entry?.paper_citation ?? c.finding_id,
        paper_year: entry?.paper_year ?? 0,
        species: entry?.species ?? null,
        n_trials: entry?.n_trials ?? null,
        mu: c.params?.mu ?? null,
        sigma: c.params?.sigma ?? null,
        threshold: c.threshold,
        gamma: c.params?.gamma ?? null,
        lapse: c.params?.lapse ?? null,
      };
    });
    const dir = sortDir === "asc" ? 1 : -1;
    rows.sort((a, b) => {
      const av = a[sortColumn];
      const bv = b[sortColumn];
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      if (typeof av === "number" && typeof bv === "number") {
        return (av - bv) * dir;
      }
      return String(av).localeCompare(String(bv)) * dir;
    });
    return rows;
  });

  function fmtNum(v: number | null, digits = 2): string {
    if (v === null || !Number.isFinite(v)) return "—";
    return v.toFixed(digits);
  }

  const fitStatusLabel = $derived(
    {
      idle: "",
      "loading-runtime": "Loading Pyodide…",
      "loading-packages": "Loading numpy + scipy…",
      fitting: "Fitting…",
      done: fitData?.pooled
        ? `Pooled bias ${fitData.pooled.params.mu.toFixed(2)}, slope σ ${fitData.pooled.params.sigma.toFixed(2)}`
        : "Done",
      error: `Error: ${fitError}`,
    }[fitStatus],
  );

  $effect(() => {
    if (!disagreementContainer || !chartReady || !vegaEmbed) return;
    if (!fitEnabled || DISAGREEMENT_VALUES.length === 0) {
      disagreementView?.finalize?.();
      disagreementView = null;
      disagreementContainer.innerHTML = "";
      return;
    }
    const xTitle = displayEntries[0]?.x_label ?? "x";
    const chrome = chartChrome();
    const tonePalette = tones();
    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height: 110,
      data: { values: DISAGREEMENT_VALUES },
      layer: [
        {
          mark: { type: "area", opacity: 0.18, color: tonePalette.warn },
          encoding: {
            x: { field: "x", type: "quantitative", title: xTitle },
            y: { field: "min", type: "quantitative", title: "Fit y" },
            y2: { field: "max" },
          },
        },
        {
          mark: { type: "line", color: tonePalette.warn, strokeWidth: 2 },
          encoding: {
            x: { field: "x", type: "quantitative", title: xTitle },
            y: { field: "std", type: "quantitative", title: "σ across curves" },
            tooltip: [
              { field: "x", title: xTitle, format: ".3f" },
              { field: "std", title: "σ across curves", format: ".3f" },
              { field: "min", title: "Min fit y", format: ".3f" },
              { field: "max", title: "Max fit y", format: ".3f" },
              { field: "n_curves", title: "Curves" },
            ],
          },
        },
      ],
      resolve: { scale: { y: "independent" as const } },
      config: {
        view: { stroke: chrome.viewStroke },
        axis: { gridColor: chrome.gridColor, labelColor: chrome.labelColor },
      },
    };
    (async () => {
      try {
        const result = await vegaEmbed(disagreementContainer, spec, {
          actions: false,
          renderer: "svg",
        });
        disagreementView?.finalize?.();
        disagreementView = result.view;
      } catch (err) {
        console.error("vega-embed (disagreement) failed", err);
      }
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
    const firstX = displayEntries[0];
    const xTitle = firstX?.x_label
      ? firstX.x_units
        ? `${firstX.x_label} (${firstX.x_units})`
        : firstX.x_label
      : "x";
    const layers: Record<string, unknown>[] = [];

    const chrome = chartChrome();
    const tonePalette = tones();
    if (fitEnabled && POOLED_BAND_VALUES.length > 0) {
      layers.push({
        data: { values: POOLED_BAND_VALUES },
        mark: { type: "area", opacity: 0.18, color: tonePalette.primary },
        encoding: {
          x: { field: "x", type: "quantitative" },
          y: { field: "lower", type: "quantitative" },
          y2: { field: "upper" },
        },
      });
    }

    // Per-point Wilson 95% CI rules. Drawn behind the line + dots so
    // they read as a quiet uncertainty signal rather than another data
    // series. Hidden when the refit pooled band is on (the band already
    // communicates uncertainty at the population level).
    const flatBoundedValues = flatBoundedPoints;
    if (!fitEnabled && flatBoundedValues.length > 0) {
      layers.push({
        data: { values: flatBoundedValues },
        transform: [
          {
            filter:
              "isValid(datum.y_lower) && isValid(datum.y_upper) && datum.y_lower !== datum.y_upper",
          },
        ],
        mark: { type: "rule", strokeWidth: 1.4, opacity: 0.4 },
        encoding: {
          x: { field: "x", type: "quantitative" },
          y: { field: "y_lower", type: "quantitative" },
          y2: { field: "y_upper" },
          color: {
            field: "paper_citation",
            type: "nominal",
            scale: { scheme: "tableau10" },
          },
          detail: { field: "finding_id", type: "nominal" },
        },
      });
    }

    layers.push({
      data: { values: points },
      transform: [{ filter: "isValid(datum.x) && isValid(datum.y)" }],
      mark: fitEnabled
        ? { type: "point", filled: true, opacity: 0.55 }
        : { type: "line", point: true, interpolate: "linear" as const },
      encoding: {
        x: { field: "x", type: "quantitative", title: xTitle },
        y: ySpec,
        color: {
          field: "paper_citation",
          type: "nominal",
          title: "Paper",
          scale: { scheme: "tableau10" },
        },
        shape: {
          field: "source_data_level",
          type: "nominal",
          title: "Source level",
        },
        detail: { field: "finding_id", type: "nominal" },
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
    });

    if (fitEnabled && FIT_LINE_VALUES.length > 0) {
      layers.push({
        data: { values: FIT_LINE_VALUES },
        mark: { type: "line", interpolate: "monotone", strokeWidth: 1.5, opacity: 0.7 },
        encoding: {
          x: { field: "x", type: "quantitative" },
          y: { field: "y", type: "quantitative" },
          color: { field: "paper_citation", type: "nominal" },
          detail: { field: "finding_id", type: "nominal" },
        },
      });
    }

    if (fitEnabled && POOLED_LINE_VALUES.length > 0) {
      layers.push({
        data: { values: POOLED_LINE_VALUES },
        mark: { type: "line", color: tonePalette.primary, strokeWidth: 3 },
        encoding: {
          x: { field: "x", type: "quantitative" },
          y: { field: "y", type: "quantitative" },
        },
      });
    }

    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height: 380,
      layer: layers,
      config: {
        view: { stroke: chrome.viewStroke },
        axis: { gridColor: chrome.gridColor, labelColor: chrome.labelColor },
        legend: { labelColor: chrome.labelColor, titleColor: chrome.titleColor },
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

<div class="rounded-md border border-rule bg-surface-raised p-4">
  <div class="mb-3 flex flex-wrap items-baseline justify-between gap-3">
    <fieldset class="flex flex-wrap items-center gap-2">
      <legend class="sr-only">View</legend>
      <span class="text-body-xs font-semibold text-fg-secondary">View:</span>
      {#each allCurveTypes as type (type)}
        <button
          type="button"
          aria-pressed={type === currentCurveType}
          class={[
            "rounded-md border px-2.5 py-1 text-body-xs",
            type === currentCurveType
              ? "border-accent bg-accent text-fg-inverse"
              : "border-rule-strong text-fg-secondary hover:bg-surface",
          ]}
          onclick={() => (currentCurveType = type)}
        >
          {type.replace(/_/g, " ")}
        </button>
      {/each}
    </fieldset>
    <div class="flex flex-wrap items-center gap-2">
      <button
        type="button"
        aria-pressed={isCurrentViewPinned}
        class={[
          "rounded-md border px-2.5 py-1 text-body-xs",
          isCurrentViewPinned
            ? "border-accent bg-accent-soft text-accent"
            : "border-rule-strong text-fg-secondary hover:bg-surface",
        ]}
        onclick={pinCurrentView}
        title={isCurrentViewPinned
          ? "View already pinned — clicking again refreshes its timestamp."
          : "Save this filter combination to your browser for quick recall."}
      >
        <span aria-hidden="true">{isCurrentViewPinned ? "★" : "☆"}</span>
        <span class="ml-1">{isCurrentViewPinned ? "Pinned" : "Pin view"}</span>
      </button>
      <button
        type="button"
        class="rounded-md border border-rule-strong px-2.5 py-1 text-body-xs text-fg-secondary hover:bg-surface"
        onclick={copyLink}
        title="Copy a shareable URL of the current view"
      >
        {copyState === "copied"
          ? "Copied ✓"
          : copyState === "error"
            ? "Copy failed"
            : "Copy link"}
      </button>
      <button
        type="button"
        class="rounded-md border border-rule-strong px-2.5 py-1 text-body-xs text-fg-secondary hover:bg-surface"
        onclick={resetFilters}
      >
        Reset filters
      </button>
    </div>
  </div>

  {#if pinnedViews.length > 0}
    <div class="mb-3 flex flex-wrap items-center gap-2 text-body-xs animate-fade-in">
      <span class="text-fg-muted">Pinned:</span>
      {#each pinnedViews as view (view.id)}
        <span
          class="inline-flex items-center gap-1 rounded-full border border-rule bg-surface-raised px-2 py-0.5 animate-fade-in"
        >
          <button
            type="button"
            class="text-fg-secondary hover:text-accent"
            onclick={() => loadPinnedView(view)}
            title={`Saved ${new Date(view.savedAt).toLocaleString()} · ${view.filterCount} filter${view.filterCount === 1 ? "" : "s"} active`}
          >
            <span aria-hidden="true" class="text-accent">★</span>
            <span class="ml-1">{view.name}</span>
          </button>
          <button
            type="button"
            class="text-fg-subtle hover:text-bad"
            onclick={() => removePinnedView(view.id)}
            aria-label={`Remove pinned view "${view.name}"`}
            title="Remove this pin"
          >
            ×
          </button>
        </span>
      {/each}
    </div>
  {/if}

  {#if axisOptionsForCurve.length > 1}
    <fieldset
      class="mb-3 ml-3 flex flex-wrap items-center gap-2 border-l-2 border-rule pl-3"
      title="Findings on different stimulus axes are kept apart — units are not comparable across paradigms."
    >
      <legend class="sr-only">Stimulus axis</legend>
      <span class="text-body-xs text-fg-muted">on axis</span>
      {#each axisOptionsForCurve as option (option.label)}
        {@const isOn = option.label === activeXLabel}
        <button
          type="button"
          aria-pressed={isOn}
          title={option.units ? `${option.label} · ${option.units}` : option.label}
          class={[
            "rounded-md border px-2 py-0.5 text-mono-id",
            isOn
              ? "border-accent bg-accent-soft text-accent"
              : "border-rule text-fg-secondary hover:border-rule-emphasis hover:text-accent",
          ]}
          onclick={() => (activeXLabel = option.label)}
        >
          {option.label}
          <span class={isOn ? "ml-1 font-mono text-accent" : "ml-1 font-mono text-fg-muted"}>
            {option.count}
          </span>
        </button>
      {/each}
    </fieldset>
  {/if}

  <div class="mb-4 flex flex-wrap items-center gap-2 text-body-xs">
    <label class="flex items-center gap-2 text-fg-secondary">
      <span class="font-semibold">Quick view:</span>
      <select
        class="rounded-md border border-rule-strong bg-surface-raised px-2 py-1 text-body-xs"
        value={presets.find((p) => isPresetActive(p.key))?.key ?? "all"}
        onchange={(event) => applyPreset((event.currentTarget as HTMLSelectElement).value as PresetKey)}
      >
        {#each presets as preset (preset.key)}
          <option value={preset.key} title={preset.description}>{preset.label}</option>
        {/each}
      </select>
    </label>
    <span class="text-fg-muted">
      Pick a hand-rolled view, or use Refine below for full filter control.
    </span>
  </div>

  <button
    type="button"
    class="mb-3 flex w-full items-center justify-between rounded-md border border-rule bg-surface px-3 py-2 text-xs text-fg-secondary hover:border-accent"
    onclick={() => (filtersExpanded = !filtersExpanded)}
    aria-expanded={filtersExpanded}
  >
    <span class="font-semibold">
      Refine
      {#if activeFilterCount > 0}
        <span class="ml-1 rounded bg-accent-soft px-1.5 py-0.5 text-[10px] text-accent">
          {activeFilterCount} active
        </span>
      {:else}
        <span class="ml-1 text-[11px] text-fg-muted">
          species · source · evidence · response · year · search
        </span>
      {/if}
    </span>
    <span aria-hidden="true">{filtersExpanded ? "−" : "+"}</span>
  </button>

  <div class={[filtersExpanded ? "block" : "hidden"]}>
    <div class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
      {#each Object.entries(filterOptions) as [key, values] (key)}
        <fieldset class="rounded border border-rule p-3">
          <legend class="px-1 text-xs font-semibold text-fg-secondary">
            {filterLabels[key as FilterKey]}
          </legend>
          <div class="mt-1 flex flex-wrap gap-x-4 gap-y-1">
            {#each values as value (value)}
              <label class="flex items-center gap-1 text-xs text-fg-secondary">
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
      <fieldset class="rounded border border-rule p-3">
        <legend class="px-1 text-xs font-semibold text-fg-secondary">Year range</legend>
        <div class="mt-1 flex items-center gap-2 text-xs text-fg-secondary">
          <input
            type="number"
            min={minYear}
            max={maxYear}
            bind:value={yearStart}
            class="w-20 rounded border border-rule px-1 py-0.5"
          />
          <span>–</span>
          <input
            type="number"
            min={minYear}
            max={maxYear}
            bind:value={yearEnd}
            class="w-20 rounded border border-rule px-1 py-0.5"
          />
          <span class="ml-2 text-[11px] text-fg-muted">
            (atlas: {minYear}–{maxYear})
          </span>
        </div>
      </fieldset>
      <fieldset class="rounded border border-rule p-3">
        <legend class="px-1 text-xs font-semibold text-fg-secondary">Search</legend>
        <input
          type="search"
          placeholder="paper / protocol / finding id…"
          bind:value={searchText}
          class="mt-1 w-full rounded border border-rule px-2 py-1 text-xs"
        />
      </fieldset>
    </div>
  </div>

  <div class="mb-2 flex flex-wrap items-center justify-between gap-3 border-t border-rule pt-3">
    <p class="text-body text-fg-secondary">
      <span class="font-semibold text-fg">
        {displayEntries.length}
        {displayEntries.length === 1 ? "trace" : "traces"}
      </span>
      <span class="text-fg-muted">
        {#if traceMode === "aggregate" && displayEntries.length !== filteredEntries.length}
          · from {filteredEntries.length}
          {currentCurveType.replace(/_/g, " ")} finding{filteredEntries.length === 1 ? "" : "s"}
        {:else}
          · {currentCurveType.replace(/_/g, " ")}
        {/if}
        · {filteredSummary.papers} paper{filteredSummary.papers === 1 ? "" : "s"}
        · {filteredSummary.species} species
        · {flatPoints.length.toLocaleString()} points
      </span>
    </p>
    <div class="flex flex-wrap items-center gap-3">
      <fieldset class="flex flex-wrap items-center gap-1 text-body-xs">
        <legend class="sr-only">Trace level</legend>
        {#each traceModeOptions as option (option.key)}
          {@const isOn = traceMode === option.key}
          <button
            type="button"
            aria-pressed={isOn}
            title={option.description}
            class={[
              "rounded-md border px-2 py-1",
              isOn
                ? "border-accent bg-accent text-fg-inverse"
                : "border-rule-strong text-fg-secondary hover:bg-surface",
            ]}
            onclick={() => (traceMode = option.key)}
          >
            {option.label}
          </button>
        {/each}
      </fieldset>
      <button
        type="button"
        aria-pressed={fitEnabled}
        title={fitEnabled
          ? "Hide the per-axis pooled fit and the per-curve refits."
          : "Refit every visible curve with a 4-parameter logistic in your browser; first toggle downloads ~10 MB of Pyodide."}
        class={[
          "inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-body-xs font-semibold transition-colors",
          fitEnabled
            ? "border-accent bg-accent text-fg-inverse hover:opacity-90"
            : "border-accent text-accent hover:bg-accent-soft",
        ]}
        onclick={() => (fitEnabled = !fitEnabled)}
      >
        {#if fitEnabled}
          <span class="inline-block h-2 w-2 rounded-full bg-fg-inverse" aria-hidden="true"></span>
          <span>Refit on</span>
        {:else}
          <span aria-hidden="true">▶</span>
          <span>Refit live in your browser</span>
        {/if}
      </button>
    </div>
  </div>

  {#if fitEnabled && fitStatus !== "idle" && fitStatus !== "done"}
    <div
      class={[
        "mb-3 flex items-center gap-3 rounded px-3 py-2 text-xs",
        fitStatus === "error"
          ? "border border-bad bg-bad-soft text-bad"
          : "border border-accent-soft bg-accent-soft text-accent",
      ]}
      role="status"
      aria-live="polite"
    >
      {#if fitStatus !== "error"}
        <span
          class="inline-block h-2 w-2 animate-pulse rounded-full bg-accent"
          aria-hidden="true"
        ></span>
      {/if}
      <span>
        {fitStatusLabel || "Working…"}
        {#if fitStatus === "loading-runtime"}
          <span class="text-fg-muted">— first toggle downloads ~10 MB Pyodide; subsequent fits are fast</span>
        {/if}
      </span>
    </div>
  {/if}

  {#if filteredEntries.length === 0}
    <div
      class="flex flex-col items-center justify-center gap-3 rounded border border-dashed border-rule-strong bg-surface px-4 py-10 text-center"
    >
      <p class="text-body text-fg-secondary">
        No findings match these filters.
      </p>
      {#if relaxationSuggestions.length > 0}
        <p class="text-body-xs text-fg-muted">Try dropping one filter:</p>
        <div class="flex flex-wrap items-center justify-center gap-2">
          {#each relaxationSuggestions as suggestion (suggestion.key)}
            <button
              type="button"
              class="rounded-md border border-accent bg-accent-soft px-3 py-1.5 text-body-xs text-accent hover:opacity-90"
              onclick={() => relaxFilter(suggestion.key)}
            >
              Drop {suggestion.label}
              <span class="ml-1 font-mono">+{suggestion.count}</span>
            </button>
          {/each}
        </div>
        {#if activeFilterCount > 0}
          <button
            type="button"
            class="rounded-md border border-rule-strong bg-surface-raised px-3 py-1 text-body-xs text-fg-secondary hover:border-rule-emphasis hover:text-accent"
            onclick={resetFilters}
          >
            Or reset all {activeFilterCount} filter{activeFilterCount === 1 ? "" : "s"}
          </button>
        {/if}
      {:else if activeFilterCount > 0}
        <button
          type="button"
          class="rounded-md border border-rule-strong bg-surface-raised px-3 py-1.5 text-body-xs text-fg-secondary hover:border-accent hover:text-accent"
          onclick={resetFilters}
        >
          Clear {activeFilterCount} active filter{activeFilterCount === 1 ? "" : "s"}
        </button>
      {:else}
        <p class="text-body-xs text-fg-muted">
          Try a different curve type above.
        </p>
      {/if}
    </div>
  {/if}
  <div class="-mx-1 overflow-x-auto px-1">
    <div
      bind:this={chartContainer}
      class={["min-w-[760px]", filteredEntries.length === 0 ? "hidden" : ""]}
    ></div>
  </div>

  {#if filteredEntries.length > 0}
    <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-fg-muted">
      <span>
        <span class="font-semibold text-fg-secondary">color</span> = paper
      </span>
      <span>
        <span class="font-semibold text-fg-secondary">shape</span> = source-data level
      </span>
      <span>
        <span class="font-semibold text-fg-secondary">trace</span> = one finding (paper × stratification)
      </span>
      {#if fitEnabled}
        <span>
          <span class="font-semibold text-fg-secondary">fit line</span> = 4-parameter logistic;
          dark line = pooled fit
        </span>
      {/if}
    </div>
  {/if}

  {#if fitEnabled && fitData?.selectionRanking && fitData.selectionRanking.length > 0}
    <div class="mt-4 animate-fade-in">
      <h3 class="mb-1 text-body-xs font-semibold text-fg-secondary">
        Live AIC ranking on the pooled curve
      </h3>
      <p class="mb-2 text-mono-id text-fg-muted">
        Each variant is fitted to the {flatPoints.length.toLocaleString()}
        pooled points using a Bernoulli log-likelihood weighted by trial count.
        The winner is the lowest-AIC entry; Δ AIC ≥ 10 is decisive, ≥ 2 is
        supported, &lt; 2 is a close call.
      </p>
      <div class="overflow-x-auto rounded-md border border-rule bg-surface-raised">
        <table class="w-full text-body-xs">
          <thead class="bg-surface text-left text-eyebrow uppercase text-fg-muted">
            <tr>
              <th class="px-3 py-2">Variant</th>
              <th class="px-3 py-2 text-right">k</th>
              <th class="px-3 py-2 text-right">log L</th>
              <th class="px-3 py-2 text-right">AIC</th>
              <th class="px-3 py-2 text-right">Δ AIC</th>
              <th class="px-3 py-2">Parameters</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-rule">
            {#each fitData.selectionRanking as row, i (row.variant)}
              {@const isWinner = i === 0}
              <tr class={isWinner ? "bg-ok-soft" : ""}>
                <td class="px-3 py-2 font-mono text-fg">
                  {#if isWinner}<span aria-hidden="true">★</span>{/if}
                  {row.label}
                </td>
                <td class="px-3 py-2 text-right font-mono">{row.n_params}</td>
                <td class="px-3 py-2 text-right font-mono">{row.log_likelihood.toFixed(1)}</td>
                <td class="px-3 py-2 text-right font-mono">{row.aic.toFixed(1)}</td>
                <td class="px-3 py-2 text-right font-mono">
                  {isWinner ? "—" : `+${row.delta_aic.toFixed(1)}`}
                </td>
                <td class="px-3 py-2 font-mono text-mono-id text-fg-secondary">
                  {Object.entries(row.params)
                    .map(([k, v]) => `${k}=${v.toFixed(3)}`)
                    .join(" · ")}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}

  {#if fitEnabled && DISAGREEMENT_VALUES.length > 0}
    <div class="mt-4">
      <h3 class="mb-1 text-body-xs font-semibold text-fg-secondary">
        Cross-paper disagreement
      </h3>
      <p class="mb-2 text-[11px] text-fg-muted">
        At each x, the orange band spans the per-curve fitted y values across
        the {DISAGREEMENT_VALUES[0]?.n_curves ?? 0} selected papers; the line
        is the across-curve standard deviation. High σ regions are where the
        literature diverges most.
      </p>
      <div class="-mx-1 overflow-x-auto px-1">
        <div bind:this={disagreementContainer} class="min-w-[760px]"></div>
      </div>
    </div>
  {/if}

  <p class="mt-3 text-[11px] text-fg-muted">
    Curves at different source-data levels are shown on shared axes for visual
    comparison; point shape encodes the source level. Values for figure-source-
    data findings should be read as published rather than as a complete raw
    behavioral export.
  </p>

  {#if fitEnabled && fitRows.length > 0}
    <div class="mt-6">
      <h3 class="mb-2 text-sm font-semibold text-fg-secondary">Fit parameters</h3>
      <p class="mb-2 text-[11px] text-fg-muted">
        Per-curve 4-parameter logistic. μ is the bias (mid-asymptote crossing);
        σ is the slope; threshold is the {fitData?.targetY === 0.84 ? "84%" : "75%"} crossing
        (in the same units as the x-axis); γ is the lower lapse, λ the upper
        lapse.
      </p>
      <div class="overflow-x-auto rounded-md border border-rule bg-surface-raised">
        <table class="w-full text-xs">
          <thead class="bg-surface text-left uppercase tracking-wide text-fg-muted">
            <tr>
              {@render sortHeader("paper_citation", "Paper", "left")}
              {@render sortHeader("paper_year", "Year", "right")}
              {@render sortHeader("n_trials", "Trials", "right")}
              {@render sortHeader("mu", "μ (bias)", "right")}
              {@render sortHeader("sigma", "σ (slope)", "right")}
              {@render sortHeader(
                "threshold",
                fitData?.targetY === 0.84 ? "x at 84%" : "x at 75%",
                "right",
              )}
              {@render sortHeader("lapse", "λ (upper lapse)", "right")}
            </tr>
          </thead>
          <tbody class="divide-y divide-rule">
            {#each fitRows as row (row.finding_id)}
              <tr>
                <td class="px-3 py-2">
                  <span class="block">{row.paper_citation}</span>
                  <span class="text-[11px] text-fg-muted">{row.species ?? "—"}</span>
                </td>
                <td class="px-3 py-2 text-right font-mono">{row.paper_year || "—"}</td>
                <td class="px-3 py-2 text-right font-mono">{row.n_trials?.toLocaleString() ?? "—"}</td>
                <td class="px-3 py-2 text-right font-mono">{fmtNum(row.mu)}</td>
                <td class="px-3 py-2 text-right font-mono">{fmtNum(row.sigma)}</td>
                <td class="px-3 py-2 text-right font-mono">{fmtNum(row.threshold)}</td>
                <td class="px-3 py-2 text-right font-mono">{fmtNum(row.lapse, 3)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>

{#snippet sortHeader(col: SortColumn, label: string, align: "left" | "right" = "left")}
  <th
    class={[
      "px-3 py-2 cursor-pointer select-none",
      align === "right" ? "text-right" : "text-left",
    ]}
    onclick={() => setSort(col)}
  >
    {label}{sortColumn === col ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
  </th>
{/snippet}
