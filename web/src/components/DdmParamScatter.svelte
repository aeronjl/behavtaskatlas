<script lang="ts">
  import { chartChrome } from "../lib/encoding";

  type DdmFitRow = {
    fit_id: string;
    variant: string;
    paper_id: string;
    paper_label: string;
    species: string;
    subject_id: string | null;
    condition: string | null;
    drift_per_unit_evidence: number;
    boundary: number;
    non_decision_time: number;
    starting_point: number | null;
    drift_bias: number | null;
    aic: number | null;
  };

  let {
    fits,
    height = 220,
  }: { fits: DdmFitRow[]; height?: number } = $props();

  let chartContainer: HTMLDivElement | undefined = $state();
  let vegaEmbed: any = null;
  let chartReady = $state(false);
  let chartView: any = null;

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
    const chrome = chartChrome();
    const params: Array<{ key: keyof DdmFitRow; title: string }> = [
      { key: "drift_per_unit_evidence", title: "k (drift / unit)" },
      { key: "boundary", title: "a (boundary)" },
      { key: "non_decision_time", title: "t0 (s)" },
    ];
    const rows = fits.flatMap((f) =>
      params.map((p) => ({
        fit_id: f.fit_id,
        variant: f.variant,
        paper_label: f.paper_label,
        species: f.species,
        subject_id: f.subject_id ?? "",
        condition: f.condition ?? "",
        param: p.title,
        value: Number(f[p.key]),
      })),
    );
    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height,
      data: { values: rows },
      facet: { column: { field: "param", title: null, sort: params.map((p) => p.title) } },
      spec: {
        width: 220,
        height,
        layer: [
          {
            mark: { type: "circle", size: 70, opacity: 0.85 },
            encoding: {
              x: { field: "value", type: "quantitative", title: null, scale: { zero: false } },
              y: {
                field: "species",
                type: "nominal",
                title: "Species",
              },
              color: {
                field: "paper_label",
                type: "nominal",
                title: "Paper",
                scale: { scheme: "tableau10" },
              },
              shape: { field: "variant", type: "nominal", title: "Variant" },
              tooltip: [
                { field: "fit_id", title: "Fit" },
                { field: "paper_label", title: "Paper" },
                { field: "variant", title: "Variant" },
                { field: "species", title: "Species" },
                { field: "subject_id", title: "Subject" },
                { field: "condition", title: "Condition" },
                { field: "value", title: "Value", format: ".4f" },
              ],
            },
          },
        ],
      },
      resolve: { scale: { x: "independent" } },
      config: {
        view: { stroke: chrome.viewStroke },
        axis: { gridColor: chrome.gridColor, labelColor: chrome.labelColor },
        legend: { labelColor: chrome.labelColor, titleColor: chrome.titleColor, orient: "right" as const },
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
        console.error("vega-embed (ddm) failed", err);
      }
    })();
  });
</script>

<div bind:this={chartContainer} class="w-full"></div>
