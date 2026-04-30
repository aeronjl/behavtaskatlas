<script lang="ts">
  import type { FindingsEntry } from "../lib/findings";

  type TraceMode = "aggregate" | "all" | "pooled";
  type GroupMode = "paper" | "protocol";
  type SourceFilter = "all" | string;

  type Point = {
    x: number;
    y: number;
    n?: number | null;
  };

  type FitSummary = {
    fit_id: string;
    variant_id: string;
    predicted_points: Point[];
  };

  type CurveCard = {
    id: string;
    title: string;
    subtitle: string;
    href: string;
    condition: string;
    traces: FindingsEntry[];
    sourceLevels: string[];
    species: string[];
    trialCount: number;
    subjectCount: number;
  };

  let {
    findings,
    defaultCurveType = "psychometric",
  }: {
    findings: FindingsEntry[];
    defaultCurveType?: string;
  } = $props();

  let curveType = $state(defaultCurveType);
  let traceMode = $state<TraceMode>("aggregate");
  let groupMode = $state<GroupMode>("paper");
  let sourceFilter = $state<SourceFilter>("all");
  let fitsEnabled = $state(true);

  const chart = {
    width: 260,
    height: 170,
    left: 34,
    right: 9,
    top: 10,
    bottom: 28,
  };
  const innerWidth = chart.width - chart.left - chart.right;
  const innerHeight = chart.height - chart.top - chart.bottom;

  const allCurveTypes = $derived.by(() =>
    Array.from(new Set(findings.map((entry) => entry.curve_type))).sort(),
  );

  const sourceOptions = $derived.by(() => [
    "all",
    ...Array.from(new Set(findings.map((entry) => entry.source_data_level))).sort(),
  ]);

  $effect(() => {
    if (allCurveTypes.length > 0 && !allCurveTypes.includes(curveType)) {
      curveType = allCurveTypes.includes(defaultCurveType)
        ? defaultCurveType
        : allCurveTypes[0];
    }
  });

  $effect(() => {
    if (!sourceOptions.includes(sourceFilter)) sourceFilter = "all";
  });

  function slugForId(id: string): string {
    return id.replace(/^[^.]+\./, "");
  }

  function findingHref(id: string): string {
    return `/findings/${slugForId(id)}`;
  }

  function paperHref(entry: FindingsEntry): string {
    return `/papers/${slugForId(entry.paper_id)}`;
  }

  function protocolHref(entry: FindingsEntry): string {
    return `/protocols/${slugForId(entry.protocol_id)}`;
  }

  function readable(value: string | null | undefined): string {
    if (!value) return "none";
    if (value === "processed-trial") return "processed trials";
    if (value === "raw-trial") return "raw trials";
    if (value === "figure-source-data") return "figure source data";
    return value.replace(/[_-]/g, " ");
  }

  function shortCitation(citation: string): string {
    const first = citation.trim().split(".")[0] ?? citation.trim();
    return first.replace(/\s+/g, " ");
  }

  function conditionKey(entry: FindingsEntry): string {
    return entry.stratification?.condition ?? "pooled";
  }

  function conditionLabel(value: string): string {
    return value === "pooled" ? "pooled" : readable(value);
  }

  function isSubjectLevel(entry: FindingsEntry): boolean {
    return Boolean(entry.stratification?.subject_id);
  }

  function sourceClass(level: string): string {
    if (level === "raw-trial") return "bg-ok-soft text-ok";
    if (level === "processed-trial") return "bg-accent-soft text-accent";
    if (level === "figure-source-data") return "bg-warn-soft text-warn";
    return "bg-slate-100 text-slate-600";
  }

  function sourceStroke(level: string): string {
    if (level === "raw-trial") return "#246b3b";
    if (level === "processed-trial") return "#2b5ea0";
    if (level === "figure-source-data") return "#b35c00";
    return "#64748b";
  }

  function fitStroke(variantId: string): string {
    if (variantId.includes("logistic")) return "#b35c00";
    if (variantId.includes("sdt")) return "#246b3b";
    if (variantId.includes("ddm")) return "#2b5ea0";
    return "#64748b";
  }

  function traceLabel(entry: FindingsEntry): string {
    const subject = entry.stratification?.subject_id;
    if (subject) return `subject ${readable(subject)}`;
    const condition = entry.stratification?.condition;
    if (condition) return readable(condition);
    return "pooled";
  }

  function groupEntries(rows: FindingsEntry[]): FindingsEntry[] {
    if (traceMode === "all") return rows;
    if (traceMode === "pooled") return rows.filter((entry) => !isSubjectLevel(entry));

    const groups = new Map<string, FindingsEntry[]>();
    for (const entry of rows) {
      const key = [
        entry.paper_id,
        entry.protocol_id,
        entry.curve_type,
        entry.x_label ?? "x",
        entry.x_units ?? "",
        conditionKey(entry),
      ].join("|");
      const group = groups.get(key) ?? [];
      group.push(entry);
      groups.set(key, group);
    }
    return Array.from(groups.values()).map(aggregateGroup);
  }

  function aggregateGroup(group: FindingsEntry[]): FindingsEntry {
    const pooled = group.find((entry) => !isSubjectLevel(entry));
    if (pooled) return pooled;

    const first = group[0];
    const pointMap = new Map<string, { x: number; ySum: number; nSum: number }>();
    for (const entry of group) {
      for (const point of entry.points) {
        const key = String(point.x);
        const acc = pointMap.get(key) ?? { x: point.x, ySum: 0, nSum: 0 };
        const weight = Math.max(point.n ?? 1, 1);
        acc.ySum += point.y * weight;
        acc.nSum += weight;
        pointMap.set(key, acc);
      }
    }

    return {
      ...first,
      finding_id: `${first.finding_id}.aggregate`,
      stratification: {
        ...first.stratification,
        subject_id: null,
      },
      points: Array.from(pointMap.values())
        .sort((a, b) => a.x - b.x)
        .map(({ x, ySum, nSum }) => ({
          x,
          y: nSum > 0 ? ySum / nSum : 0,
          n: nSum,
          y_lower: null,
          y_upper: null,
        })),
      n_trials: group.reduce(
        (sum, entry) =>
          sum + (typeof entry.n_trials === "number" ? entry.n_trials : 0),
        0,
      ),
      n_subjects: group.length,
      model_fits: [],
    } as FindingsEntry;
  }

  const filteredFindings = $derived.by(() =>
    findings.filter(
      (entry) =>
        entry.curve_type === curveType &&
        (sourceFilter === "all" || entry.source_data_level === sourceFilter),
    ),
  );

  const traceFindings = $derived.by(() => groupEntries(filteredFindings));

  const cards = $derived.by<CurveCard[]>(() => {
    const grouped = new Map<string, FindingsEntry[]>();
    for (const entry of traceFindings) {
      const scopeId = groupMode === "paper" ? entry.paper_id : entry.protocol_id;
      const key = `${scopeId}|${conditionKey(entry)}`;
      const group = grouped.get(key) ?? [];
      group.push(entry);
      grouped.set(key, group);
    }

    return Array.from(grouped.entries())
      .map(([id, traces]) => {
        const first = traces[0];
        const sourceLevels = Array.from(
          new Set(traces.map((entry) => entry.source_data_level)),
        ).sort();
        const species = Array.from(
          new Set(traces.map((entry) => entry.species ?? "unknown")),
        ).sort();
        const condition = conditionKey(first);
        const uniqueSubjects = new Set(
          traces
            .map((entry) => entry.stratification?.subject_id)
            .filter((value): value is string => Boolean(value)),
        );
        const subjectCount =
          uniqueSubjects.size > 0
            ? uniqueSubjects.size
            : Math.max(0, ...traces.map((entry) => entry.n_subjects ?? 0));

        return {
          id,
          title:
            groupMode === "paper" ? shortCitation(first.paper_citation) : first.protocol_name,
          subtitle:
            groupMode === "paper"
              ? `${first.paper_year} - ${first.protocol_name}`
              : `${traces.length} trace${traces.length === 1 ? "" : "s"} - ${shortCitation(first.paper_citation)}`,
          href: groupMode === "paper" ? paperHref(first) : protocolHref(first),
          condition: conditionLabel(condition),
          traces: traces.sort((a, b) => {
            const aSubject = a.stratification?.subject_id ?? "";
            const bSubject = b.stratification?.subject_id ?? "";
            return a.paper_year - b.paper_year || aSubject.localeCompare(bSubject);
          }),
          sourceLevels,
          species,
          trialCount: traces.reduce(
            (sum, entry) =>
              sum + (typeof entry.n_trials === "number" ? entry.n_trials : 0),
            0,
          ),
          subjectCount,
        };
      })
      .sort((a, b) => {
        const yearA = a.traces[0]?.paper_year ?? 0;
        const yearB = b.traces[0]?.paper_year ?? 0;
        return yearA - yearB || a.title.localeCompare(b.title) || a.condition.localeCompare(b.condition);
      });
  });

  function fitsFor(entry: FindingsEntry): FitSummary[] {
    return (((entry as unknown as { model_fits?: FitSummary[] }).model_fits ?? [])
      .filter((fit) => (fit.predicted_points ?? []).length > 0));
  }

  const domain = $derived.by(() => {
    const allPoints = cards.flatMap((card) =>
      card.traces.flatMap((entry) => [
        ...entry.points,
        ...(fitsEnabled ? fitsFor(entry).flatMap((fit) => fit.predicted_points) : []),
      ]),
    );
    const xs = allPoints.map((point) => point.x).filter(Number.isFinite);
    const ys = allPoints.map((point) => point.y).filter(Number.isFinite);
    const xMin = Math.min(...xs, 0);
    const xMax = Math.max(...xs, 1);
    if (curveType === "psychometric" || curveType === "accuracy_by_strength") {
      return { xMin, xMax, yMin: 0, yMax: 1 };
    }
    const yMin = Math.min(...ys, 0);
    const yMaxRaw = Math.max(...ys, 1);
    const pad = Math.max((yMaxRaw - yMin) * 0.08, 0.05);
    return { xMin, xMax, yMin: Math.max(0, yMin - pad), yMax: yMaxRaw + pad };
  });

  function xPos(value: number): number {
    if (!Number.isFinite(value)) return chart.left;
    if (domain.xMax === domain.xMin) return chart.left + innerWidth / 2;
    return chart.left + ((value - domain.xMin) / (domain.xMax - domain.xMin)) * innerWidth;
  }

  function yPos(value: number): number {
    if (!Number.isFinite(value)) return chart.top + innerHeight;
    if (domain.yMax === domain.yMin) return chart.top + innerHeight / 2;
    return chart.top + innerHeight - ((value - domain.yMin) / (domain.yMax - domain.yMin)) * innerHeight;
  }

  function linePath(points: Point[]): string {
    const sorted = points
      .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y))
      .sort((a, b) => a.x - b.x);
    return sorted
      .map((point, index) => `${index === 0 ? "M" : "L"}${xPos(point.x).toFixed(1)},${yPos(point.y).toFixed(1)}`)
      .join(" ");
  }

  function axisLabel(value: number): string {
    if (Math.abs(value) >= 1000) return value.toFixed(0);
    if (Math.abs(value) >= 10) return value.toFixed(0);
    return value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  }
</script>

{#if findings.length === 0}
  <p class="rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-500">
    No findings linked yet.
  </p>
{:else}
  <div class="mb-3 flex flex-wrap items-center gap-2">
    <div class="flex flex-wrap gap-1" role="group" aria-label="Curve type">
      {#each allCurveTypes as type (type)}
        <button
          type="button"
          aria-pressed={curveType === type}
          class={[
            "rounded border px-2 py-1 text-xs",
            curveType === type
              ? "border-accent bg-accent text-white"
              : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
          ]}
          onclick={() => (curveType = type)}
        >
          {readable(type)}
        </button>
      {/each}
    </div>

    <div class="flex flex-wrap gap-1" role="group" aria-label="Panel grouping">
      <button
        type="button"
        aria-pressed={groupMode === "paper"}
        class={[
          "rounded border px-2 py-1 text-xs",
          groupMode === "paper"
            ? "border-accent bg-accent text-white"
            : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
        ]}
        onclick={() => (groupMode = "paper")}
      >
        by paper
      </button>
      <button
        type="button"
        aria-pressed={groupMode === "protocol"}
        class={[
          "rounded border px-2 py-1 text-xs",
          groupMode === "protocol"
            ? "border-accent bg-accent text-white"
            : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
        ]}
        onclick={() => (groupMode = "protocol")}
      >
        by protocol
      </button>
    </div>

    <div class="flex flex-wrap gap-1" role="group" aria-label="Trace display">
      <button
        type="button"
        aria-pressed={traceMode === "aggregate"}
        class={[
          "rounded border px-2 py-1 text-xs",
          traceMode === "aggregate"
            ? "border-accent bg-accent text-white"
            : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
        ]}
        onclick={() => (traceMode = "aggregate")}
      >
        per condition
      </button>
      <button
        type="button"
        aria-pressed={traceMode === "all"}
        class={[
          "rounded border px-2 py-1 text-xs",
          traceMode === "all"
            ? "border-accent bg-accent text-white"
            : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
        ]}
        onclick={() => (traceMode = "all")}
      >
        all traces
      </button>
      <button
        type="button"
        aria-pressed={traceMode === "pooled"}
        class={[
          "rounded border px-2 py-1 text-xs",
          traceMode === "pooled"
            ? "border-accent bg-accent text-white"
            : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
        ]}
        onclick={() => (traceMode = "pooled")}
      >
        pooled only
      </button>
    </div>

    <label class="ml-auto flex items-center gap-1 text-xs text-slate-700">
      <input type="checkbox" bind:checked={fitsEnabled} />
      <span>fits</span>
    </label>

    <label class="flex items-center gap-1 text-xs text-slate-700">
      <span>source</span>
      <select
        bind:value={sourceFilter}
        class="rounded border border-slate-300 bg-white px-2 py-1 text-xs"
      >
        {#each sourceOptions as option (option)}
          <option value={option}>{option === "all" ? "all" : readable(option)}</option>
        {/each}
      </select>
    </label>
  </div>

  <div class="mb-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
    <span>{cards.length} panel{cards.length === 1 ? "" : "s"}</span>
    <span>{traceFindings.length} trace{traceFindings.length === 1 ? "" : "s"}</span>
    {#each sourceOptions.filter((option) => option !== "all") as source (source)}
      <span class="inline-flex items-center gap-1">
        <span
          class="h-2 w-2 rounded-full"
          style={`background: ${sourceStroke(source)}`}
        ></span>
        {readable(source)}
      </span>
    {/each}
  </div>

  {#if cards.length === 0}
    <p class="rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-500">
      No curves match the selected controls.
    </p>
  {:else}
    <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {#each cards as card (card.id)}
        <article class="rounded-md border border-slate-200 bg-white p-3">
          <header class="mb-2 min-h-20">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <h3 class="line-clamp-2 text-sm font-semibold leading-snug text-slate-900">
                  <a class="no-underline hover:text-accent" href={card.href}>
                    {card.title}
                  </a>
                </h3>
                <p class="mt-1 line-clamp-2 text-[11px] text-slate-500">
                  {card.subtitle}
                </p>
              </div>
              <span class="shrink-0 rounded bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                {card.condition}
              </span>
            </div>
            <div class="mt-2 flex flex-wrap gap-1">
              {#each card.sourceLevels as level (level)}
                <span class={`rounded px-2 py-0.5 text-[11px] ${sourceClass(level)}`}>
                  {readable(level)}
                </span>
              {/each}
              {#each card.species as species (species)}
                <span class="rounded bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                  {readable(species)}
                </span>
              {/each}
            </div>
          </header>

          <svg
            class="h-44 w-full overflow-visible"
            viewBox={`0 0 ${chart.width} ${chart.height}`}
            role="img"
            aria-label={`${card.title}, ${card.condition}, ${card.traces.length} traces`}
          >
            <rect
              x={chart.left}
              y={chart.top}
              width={innerWidth}
              height={innerHeight}
              fill="#fff"
              stroke="#cbd5e1"
            />
            {#each [0, 0.5, 1] as fraction (fraction)}
              {@const y = chart.top + innerHeight * fraction}
              <line
                x1={chart.left}
                x2={chart.left + innerWidth}
                y1={y}
                y2={y}
                stroke="#e2e8f0"
                stroke-width="0.8"
              />
            {/each}
            <line
              x1={chart.left}
              x2={chart.left + innerWidth}
              y1={chart.top + innerHeight}
              y2={chart.top + innerHeight}
              stroke="#94a3b8"
            />
            <line
              x1={chart.left}
              x2={chart.left}
              y1={chart.top}
              y2={chart.top + innerHeight}
              stroke="#94a3b8"
            />
            <text x={chart.left - 6} y={chart.top + 4} text-anchor="end" font-size="9" fill="#64748b">
              {axisLabel(domain.yMax)}
            </text>
            <text x={chart.left - 6} y={chart.top + innerHeight + 3} text-anchor="end" font-size="9" fill="#64748b">
              {axisLabel(domain.yMin)}
            </text>
            <text x={chart.left} y={chart.height - 8} text-anchor="middle" font-size="9" fill="#64748b">
              {axisLabel(domain.xMin)}
            </text>
            <text x={chart.left + innerWidth} y={chart.height - 8} text-anchor="middle" font-size="9" fill="#64748b">
              {axisLabel(domain.xMax)}
            </text>

            {#each card.traces as trace (trace.finding_id)}
              {@const observedPath = linePath(trace.points)}
              {#if fitsEnabled}
                {#each fitsFor(trace) as fit (fit.fit_id)}
                  {@const fitPath = linePath(fit.predicted_points)}
                  {#if fitPath}
                    <path
                      d={fitPath}
                      fill="none"
                      stroke={fitStroke(fit.variant_id)}
                      stroke-width="1.1"
                      stroke-dasharray="3 3"
                      opacity="0.52"
                    >
                      <title>
                        {fit.variant_id.replace("model_variant.", "")}
                      </title>
                    </path>
                  {/if}
                {/each}
              {/if}
              <a href={findingHref(trace.finding_id)} aria-label={`${traceLabel(trace)} finding`}>
                {#if observedPath}
                  <path
                    d={observedPath}
                    fill="none"
                    stroke={sourceStroke(trace.source_data_level)}
                    stroke-width={isSubjectLevel(trace) ? 1 : 1.8}
                    opacity={isSubjectLevel(trace) ? 0.48 : 0.92}
                  >
                    <title>
                      {traceLabel(trace)} - {readable(trace.source_data_level)}
                    </title>
                  </path>
                {/if}
                {#each trace.points as point, pointIndex (`${trace.finding_id}-${pointIndex}`)}
                  {#if Number.isFinite(point.x) && Number.isFinite(point.y)}
                    <circle
                      cx={xPos(point.x)}
                      cy={yPos(point.y)}
                      r={isSubjectLevel(trace) ? 1.4 : 2.1}
                      fill={sourceStroke(trace.source_data_level)}
                      opacity={isSubjectLevel(trace) ? 0.5 : 0.95}
                    />
                  {/if}
                {/each}
              </a>
            {/each}
          </svg>

          <footer class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
            <span>{card.traces.length} trace{card.traces.length === 1 ? "" : "s"}</span>
            {#if card.subjectCount > 0}
              <span>{card.subjectCount} subject{card.subjectCount === 1 ? "" : "s"}</span>
            {/if}
            {#if card.trialCount > 0}
              <span>{card.trialCount.toLocaleString()} trials</span>
            {/if}
          </footer>
        </article>
      {/each}
    </div>
  {/if}
{/if}
