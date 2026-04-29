<script lang="ts">
  type ResidualRow = {
    fit_id: string;
    variant: string;
    x: number;
    observed: number;
    predicted: number;
    residual: number;
  };

  let {
    rows,
    xLabel = "x",
    height = 220,
  }: {
    rows: ResidualRow[];
    xLabel?: string;
    height?: number;
  } = $props();

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
    if (rows.length === 0) {
      chartView?.finalize?.();
      chartView = null;
      chartContainer.innerHTML = "";
      return;
    }
    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height,
      data: { values: rows },
      layer: [
        {
          mark: { type: "rule", color: "#94a3b8" },
          encoding: { y: { datum: 0 } },
        },
        {
          mark: { type: "line", point: true },
          encoding: {
            x: { field: "x", type: "quantitative", title: xLabel },
            y: {
              field: "residual",
              type: "quantitative",
              title: "predicted - observed",
            },
            color: {
              field: "variant",
              type: "nominal",
              title: "Variant",
              scale: { scheme: "tableau10" },
            },
            detail: { field: "fit_id", type: "nominal" },
            tooltip: [
              { field: "variant", title: "Variant" },
              { field: "x", title: xLabel, format: ".3f" },
              { field: "observed", title: "Observed", format: ".4f" },
              { field: "predicted", title: "Predicted", format: ".4f" },
              { field: "residual", title: "Residual", format: ".4f" },
            ],
          },
        },
      ],
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
        console.error("vega-embed residual plot failed", err);
      }
    })();
  });
</script>

{#if rows.length === 0}
  <p class="rounded-md border border-slate-200 bg-white p-3 text-xs text-slate-500">
    No residual points available.
  </p>
{:else}
  <div class="rounded-md border border-slate-200 bg-white p-3">
    <div bind:this={chartContainer} class="w-full"></div>
  </div>
{/if}
