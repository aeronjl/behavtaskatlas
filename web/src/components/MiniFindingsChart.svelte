<script lang="ts">
  import type { FindingsEntry } from "../lib/findings";

  type ColorBy = "paper" | "curve_type" | "condition";

  let {
    findings,
    title,
    colorBy = "paper",
    height = 240,
  }: {
    findings: FindingsEntry[];
    title?: string;
    colorBy?: ColorBy;
    height?: number;
  } = $props();

  const allCurveTypes = Array.from(
    new Set(findings.map((f) => f.curve_type)),
  ).sort();

  let currentCurveType = $state<string>(
    allCurveTypes.includes("psychometric")
      ? "psychometric"
      : (allCurveTypes[0] ?? "psychometric"),
  );

  const visibleFindings = $derived(
    findings.filter((f) => f.curve_type === currentCurveType),
  );

  const flatPoints = $derived.by(() =>
    visibleFindings.flatMap((entry) =>
      entry.points.map((p) => ({
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
      })),
    ),
  );

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

    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height,
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
      config: {
        view: { stroke: "#cbd5e1" },
        axis: { gridColor: "#e2e8f0", labelColor: "#334155" },
        legend: {
          labelColor: "#334155",
          titleColor: "#0f172a",
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
  <p class="rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-500">
    No findings linked yet.
  </p>
{:else}
  <div class="rounded-md border border-slate-200 bg-white p-3">
    {#if title || allCurveTypes.length > 1}
      <header class="mb-2 flex flex-wrap items-baseline gap-2">
        {#if title}
          <h3 class="text-sm font-semibold text-slate-700">{title}</h3>
        {/if}
        {#if allCurveTypes.length > 1}
          <div class="flex flex-wrap gap-1 ml-auto">
            {#each allCurveTypes as type (type)}
              <button
                type="button"
                class:list={[
                  "rounded border px-2 py-0.5 text-[11px]",
                  type === currentCurveType
                    ? "border-accent bg-accent text-white"
                    : "border-slate-300 text-slate-700 hover:bg-slate-50",
                ]}
                onclick={() => (currentCurveType = type)}
              >
                {type.replace(/_/g, " ")}
              </button>
            {/each}
          </div>
        {/if}
      </header>
    {/if}
    <div bind:this={chartContainer} class="w-full"></div>
  </div>
{/if}
