<!--
  ThresholdDistribution — strip plot of 75% thresholds across the
  atlas's psychometric findings.

  The single number "median 75% threshold = 0.27 (signed coherence)"
  begs to be read as a distribution; this component renders one
  jittered point per finding-with-a-fit, coloured by species, with a
  vertical rule at the median. Clicking a point navigates to that
  finding's detail page so the chart is also a discovery affordance.

  Inputs are passed in pre-shaped from the page so we don't import
  the full findings index into this component.
-->
<script lang="ts">
  import { chartChrome, tones } from "../lib/encoding";

  type Row = {
    finding_id: string;
    href: string;
    paper_label: string;
    species: string;
    threshold: number;
  };

  interface Props {
    rows: Row[];
    median: number | null;
    /** Axis label from the canonical x_label of the dominant axis. */
    xLabel?: string;
    height?: number;
  }

  let { rows, median, xLabel = "x at 75%", height = 220 }: Props = $props();

  let container: HTMLDivElement | undefined = $state();
  let vegaEmbed: any = null;
  let view: any = null;

  $effect(() => {
    if (!container) return;
    if (vegaEmbed) return;
    (async () => {
      const mod = await import("vega-embed");
      vegaEmbed = mod.default ?? mod;
      render();
    })();
  });

  $effect(() => {
    void rows;
    void median;
    void xLabel;
    if (!vegaEmbed || !container) return;
    render();
  });

  function render() {
    if (!container || !vegaEmbed) return;
    const chrome = chartChrome();
    const tonePalette = tones();
    const layers: Record<string, unknown>[] = [];
    if (median !== null && Number.isFinite(median)) {
      layers.push({
        data: { values: [{ x: median }] },
        mark: { type: "rule", color: tonePalette.muted, strokeDash: [4, 4] },
        encoding: {
          x: { field: "x", type: "quantitative" },
        },
      });
    }
    layers.push({
      data: { values: rows },
      mark: {
        type: "point",
        filled: true,
        size: 90,
        opacity: 0.85,
      },
      encoding: {
        x: {
          field: "threshold",
          type: "quantitative",
          title: xLabel,
        },
        yOffset: {
          // Vertical jitter keeps overlapping points visible without
          // pretending the y-axis carries information.
          field: "finding_id",
          type: "nominal",
        },
        color: {
          field: "species",
          type: "nominal",
          title: "Species",
          scale: { scheme: "tableau10" },
          legend: { orient: "right" },
        },
        href: { field: "href", type: "nominal" },
        tooltip: [
          { field: "paper_label", title: "Paper" },
          { field: "species", title: "Species" },
          { field: "threshold", title: xLabel, format: ".3f" },
          { field: "finding_id", title: "Finding" },
        ],
      },
    });
    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height,
      layer: layers,
      config: {
        view: { stroke: chrome.viewStroke },
        axis: { gridColor: chrome.gridColor, labelColor: chrome.labelColor },
        legend: { labelColor: chrome.labelColor, titleColor: chrome.titleColor },
      },
    };
    (async () => {
      try {
        const result = await vegaEmbed(container, spec, {
          actions: false,
          renderer: "svg",
        });
        view?.finalize?.();
        view = result.view;
      } catch (err) {
        console.error("ThresholdDistribution vega-embed failed", err);
      }
    })();
  }
</script>

{#if rows.length === 0}
  <p class="text-body-xs text-fg-muted">
    No psychometric findings have fits yet.
  </p>
{:else}
  <div bind:this={container} class="w-full"></div>
  <p class="mt-2 text-mono-id text-fg-muted">
    Each point is one finding's fitted x-at-75%. Click a point to open
    its detail page. Dashed line marks the across-finding median.
  </p>
{/if}
