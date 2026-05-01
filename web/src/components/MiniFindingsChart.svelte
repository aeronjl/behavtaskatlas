<script lang="ts">
  import type { FindingsEntry } from "../lib/findings";
  import { chartChrome } from "../lib/encoding";

  type ColorBy = "paper" | "curve_type" | "condition";
  type TraceMode = "aggregate" | "all" | "pooled";

  let {
    findings,
    title,
    colorBy = "paper",
    height = 240,
    showFits = false,
    defaultTraceMode = "aggregate",
    showTraceControls = true,
  }: {
    findings: FindingsEntry[];
    title?: string;
    colorBy?: ColorBy;
    height?: number;
    showFits?: boolean;
    defaultTraceMode?: TraceMode;
    showTraceControls?: boolean;
  } = $props();

  type FitSummary = {
    fit_id: string;
    variant_id: string;
    family_id: string;
    parameters: Record<string, number>;
    quality: Record<string, number>;
    predicted_points: Array<{ x: number; y: number; n: number }>;
  };
  let fitsEnabled = $state(false);
  let traceMode = $state<TraceMode>("aggregate");
  let currentCurveType = $state<string>("");

  $effect(() => {
    fitsEnabled = showFits;
  });

  $effect(() => {
    traceMode = defaultTraceMode;
  });

  const allCurveTypes = $derived.by(() =>
    Array.from(new Set(findings.map((f) => f.curve_type))).sort(),
  );

  const defaultCurveType = $derived(
    allCurveTypes.includes("psychometric")
      ? "psychometric"
      : (allCurveTypes[0] ?? "psychometric"),
  );

  $effect(() => {
    if (allCurveTypes.length === 0) {
      currentCurveType = "";
      return;
    }
    if (!currentCurveType || !allCurveTypes.includes(currentCurveType)) {
      currentCurveType = defaultCurveType;
    }
  });

  const rawVisibleFindings = $derived(
    findings.filter((f) => f.curve_type === currentCurveType),
  );

  function isSubjectLevel(entry: FindingsEntry): boolean {
    return Boolean(entry.stratification?.subject_id);
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
    const points = Array.from(pointMap.values())
      .sort((a, b) => a.x - b.x)
      .map(({ x, ySum, nSum }) => ({
        x,
        y: nSum > 0 ? ySum / nSum : 0,
        n: nSum,
        y_lower: null,
        y_upper: null,
      }));
    return {
      ...first,
      finding_id: `${first.paper_id}|${first.curve_type}|${first.stratification?.condition ?? ""}|mini-aggregate`,
      stratification: {
        condition: first.stratification?.condition ?? null,
        subject_id: null,
      },
      points,
      n_trials: group.reduce(
        (sum, entry) =>
          sum + (typeof entry.n_trials === "number" ? entry.n_trials : 0),
        0,
      ),
      n_subjects: group.length,
      model_fits: [],
    } as FindingsEntry;
  }

  const visibleFindings = $derived.by<FindingsEntry[]>(() => {
    if (traceMode === "all") return rawVisibleFindings;
    if (traceMode === "pooled") {
      return rawVisibleFindings.filter((entry) => !isSubjectLevel(entry));
    }
    const groups = new Map<string, FindingsEntry[]>();
    for (const entry of rawVisibleFindings) {
      const key = [
        entry.paper_id,
        entry.curve_type,
        entry.x_label ?? "x",
        entry.x_units ?? "",
        entry.stratification?.condition ?? "",
      ].join("|");
      const list = groups.get(key) ?? [];
      list.push(entry);
      groups.set(key, list);
    }
    return Array.from(groups.values()).map(aggregateGroup);
  });

  const traceControlsVisible = $derived(
    showTraceControls &&
      rawVisibleFindings.length > 1 &&
      (rawVisibleFindings.some(isSubjectLevel) ||
        visibleFindings.length !== rawVisibleFindings.length ||
        traceMode !== "aggregate"),
  );

  // Curve types whose y values are sample proportions of binary trial
  // outcomes — Wilson 95% CIs are well-defined when n is known. RT-based
  // curves (chronometric, etc.) need a separate distributional assumption
  // and are left without computed bounds.
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

  // Resolve a CI for a single observed point. Prefer authored bounds
  // (`y_lower` / `y_upper` on the YAML record) over our runtime Wilson
  // estimate so a curator can override the default CI when they have
  // a better one (bootstrap, mixed-effects, etc.). Returns null when
  // the curve type isn't binary and no authored bounds exist.
  function pointBounds(
    curveType: string,
    point: FindingsEntry["points"][number],
  ): { lower: number; upper: number } | null {
    const lower = (point as { y_lower?: number | null }).y_lower;
    const upper = (point as { y_upper?: number | null }).y_upper;
    if (
      lower !== null &&
      lower !== undefined &&
      upper !== null &&
      upper !== undefined
    ) {
      return { lower, upper };
    }
    if (BINARY_CURVE_TYPES.has(curveType)) {
      return wilsonInterval(point.y, point.n);
    }
    return null;
  }

  const flatPoints = $derived.by(() =>
    visibleFindings.flatMap((entry) =>
      entry.points.map((p) => {
        const bounds = pointBounds(entry.curve_type, p);
        return {
          finding_id: entry.finding_id,
          paper_citation: entry.paper_citation,
          paper_year: entry.paper_year,
          curve_type: entry.curve_type,
          condition_label:
            entry.stratification?.condition ??
            entry.stratification?.subject_id ??
            entry.protocol_name,
          species: entry.species ?? "unknown",
          source_data_level: entry.source_data_level,
          protocol_name: entry.protocol_name,
          x: p.x,
          y: p.y,
          n: p.n,
          y_lower: bounds?.lower ?? null,
          y_upper: bounds?.upper ?? null,
        };
      }),
    ),
  );

  const flatBoundedPoints = $derived(
    flatPoints.filter((p) => p.y_lower !== null && p.y_upper !== null),
  );

  const flatFitPoints = $derived.by(() =>
    visibleFindings.flatMap((entry) => {
      const fits = ((entry as unknown as { model_fits?: FitSummary[] }).model_fits ?? []) as FitSummary[];
      return fits.flatMap((fit) =>
        (fit.predicted_points ?? []).map((p) => ({
          fit_key: `${entry.finding_id}__${fit.fit_id}`,
          finding_id: entry.finding_id,
          variant: fit.variant_id.replace("model_variant.", ""),
          paper_citation: entry.paper_citation,
          x: p.x,
          y: p.y,
        })),
      );
    }),
  );

  const anyFitsAvailable = $derived(flatFitPoints.length > 0);

  const colorFieldFor: Record<ColorBy, string> = {
    paper: "paper_citation",
    curve_type: "curve_type",
    condition: "condition_label",
  };
  const colorTitleFor: Record<ColorBy, string> = {
    paper: "Paper",
    curve_type: "Curve type",
    condition: "Condition",
  };

  let chartContainer: HTMLDivElement | undefined = $state();
  let vegaEmbed: any = null;
  let chartView: any = null;
  let chartReady = $state(false);

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
    if (visibleFindings.length === 0) {
      chartView?.finalize?.();
      chartView = null;
      chartContainer.innerHTML = "";
      return;
    }
    const xLabel = visibleFindings[0]?.x_label ?? "x";
    const yLabel = visibleFindings[0]?.y_label ?? "y";
    const yScale =
      currentCurveType === "psychometric" ||
      currentCurveType === "accuracy_by_strength"
        ? { domain: [0, 1] }
        : undefined;
    const ySpec: Record<string, unknown> = {
      field: "y",
      type: "quantitative",
      title: yLabel,
    };
    if (yScale) ySpec.scale = yScale;

    const dataLayer: Record<string, unknown> = {
      data: { values: flatPoints },
      transform: [{ filter: "isValid(datum.x) && isValid(datum.y)" }],
      mark: { type: "line", point: true, interpolate: "linear" as const },
      encoding: {
        x: { field: "x", type: "quantitative", title: xLabel },
        y: ySpec,
        color: {
          field: colorFieldFor[colorBy],
          type: "nominal",
          title: colorTitleFor[colorBy],
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
          { field: "condition_label", title: "Condition" },
          { field: "source_data_level", title: "Source level" },
          { field: "x", title: xLabel, format: ".3f" },
          { field: "y", title: yLabel, format: ".3f" },
          { field: "n", title: "n" },
        ],
      },
    };

    const layers: Array<Record<string, unknown>> = [];

    // CI rule layer first so it sits behind the line + dots.
    if (flatBoundedPoints.length > 0) {
      layers.push({
        data: { values: flatBoundedPoints },
        transform: [
          {
            filter:
              "isValid(datum.y_lower) && isValid(datum.y_upper) && datum.y_lower !== datum.y_upper",
          },
        ],
        mark: { type: "rule", strokeWidth: 1.4, opacity: 0.45 },
        encoding: {
          x: { field: "x", type: "quantitative" },
          y: { field: "y_lower", type: "quantitative" },
          y2: { field: "y_upper" },
          color: {
            field: colorFieldFor[colorBy],
            type: "nominal",
            scale: { scheme: "tableau10" },
          },
          detail: { field: "finding_id", type: "nominal" },
        },
      });
    }

    layers.push(dataLayer);

    if (fitsEnabled && flatFitPoints.length > 0) {
      layers.push({
        data: { values: flatFitPoints },
        transform: [{ filter: "isValid(datum.x) && isValid(datum.y)" }],
        mark: {
          type: "line",
          interpolate: "linear" as const,
          strokeDash: [4, 4],
          opacity: 0.85,
        },
        encoding: {
          x: { field: "x", type: "quantitative" },
          y: { field: "y", type: "quantitative" },
          detail: { field: "fit_key", type: "nominal" },
          color: {
            field: "variant",
            type: "nominal",
            title: "Fit variant",
            scale: { scheme: "tableau20" },
          },
          tooltip: [
            { field: "paper_citation", title: "Paper" },
            { field: "variant", title: "Variant" },
            { field: "x", title: xLabel, format: ".3f" },
            { field: "y", title: "Predicted y", format: ".3f" },
          ],
        },
      });
    }

    const chrome = chartChrome();
    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height,
      resolve: { scale: { color: "independent" } },
      layer: layers,
      config: {
        view: { stroke: chrome.viewStroke },
        axis: { gridColor: chrome.gridColor, labelColor: chrome.labelColor },
        legend: {
          labelColor: chrome.labelColor,
          titleColor: chrome.titleColor,
          orient: "right" as const,
        },
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
        console.error("vega-embed (mini) failed", err);
      }
    })();
  });
</script>

{#if findings.length === 0}
  <p class="rounded-md border border-rule bg-surface-raised p-3 text-xs text-fg-muted">
    No findings linked yet.
  </p>
{:else}
  <div class="rounded-md border border-rule bg-surface-raised p-3">
    {#if title || allCurveTypes.length > 1 || anyFitsAvailable || traceControlsVisible}
      <header class="mb-2 flex flex-wrap items-center gap-2">
        {#if title}
          <h3 class="text-sm font-semibold text-fg-secondary">{title}</h3>
        {/if}
        {#if allCurveTypes.length > 1}
          <div class="flex flex-wrap gap-1 {title ? '' : 'mr-auto'}">
            {#each allCurveTypes as type (type)}
              <button
                type="button"
                class={[
                  "rounded border px-2 py-0.5 text-[11px]",
                  type === currentCurveType
                    ? "border-accent bg-accent text-white"
                    : "border-rule-strong text-fg-secondary hover:bg-surface",
                ]}
                onclick={() => (currentCurveType = type)}
              >
                {type.replace(/_/g, " ")}
              </button>
            {/each}
          </div>
        {/if}
        {#if traceControlsVisible}
          <div class="ml-auto flex flex-wrap gap-1 text-[11px]">
            <button
              type="button"
              class={[
                "rounded border px-2 py-0.5",
                traceMode === "aggregate"
                  ? "border-accent bg-accent text-white"
                  : "border-rule-strong text-fg-secondary hover:bg-surface",
              ]}
              onclick={() => (traceMode = "aggregate")}
              title="One trace per paper × condition; subject curves are pooled when needed."
            >
              per condition
            </button>
            <button
              type="button"
              class={[
                "rounded border px-2 py-0.5",
                traceMode === "all"
                  ? "border-accent bg-accent text-white"
                  : "border-rule-strong text-fg-secondary hover:bg-surface",
              ]}
              onclick={() => (traceMode = "all")}
              title="Show every curated finding separately."
            >
              all curves
            </button>
            <button
              type="button"
              class={[
                "rounded border px-2 py-0.5",
                traceMode === "pooled"
                  ? "border-accent bg-accent text-white"
                  : "border-rule-strong text-fg-secondary hover:bg-surface",
              ]}
              onclick={() => (traceMode = "pooled")}
              title="Only show published pooled curves."
            >
              pooled only
            </button>
          </div>
        {/if}
        {#if anyFitsAvailable}
          <label class="{traceControlsVisible ? '' : 'ml-auto'} flex items-center gap-1 text-[11px] text-fg-secondary">
            <input type="checkbox" bind:checked={fitsEnabled} />
            <span>show fits</span>
          </label>
        {/if}
      </header>
    {/if}
    {#if visibleFindings.length !== rawVisibleFindings.length}
      <p class="mb-2 text-[11px] text-fg-muted">
        Showing {visibleFindings.length} trace{visibleFindings.length === 1 ? "" : "s"}
        from {rawVisibleFindings.length} finding{rawVisibleFindings.length === 1 ? "" : "s"}.
      </p>
    {/if}
    <div class="-mx-1 overflow-x-auto px-1">
      <div bind:this={chartContainer} class="min-w-[680px]"></div>
    </div>
  </div>
{/if}
