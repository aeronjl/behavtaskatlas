<!--
  AggregateBySpecies — a small Vega-Lite chart that replaces the
  per-species `<ul>` on the homepage's "Across the literature" panel.

  The list version was hard to scan; a chart of median σ per species
  with strip-overlay individual points reads as one shape and lets
  the visitor see whether spread varies by species. Click any species
  label to filter findings.

  Inputs are pre-shaped from the page so we don't import the full
  findings index. Each row carries: species, sigmas (per finding),
  thresholds (per finding), n_findings, total_trials, href.
-->
<script lang="ts">
  import { chartChrome, tones } from "../lib/encoding";

  type Row = {
    species: string;
    href: string;
    n_findings: number;
    total_trials: number;
    median_sigma: number | null;
    median_threshold: number | null;
    sigmas: number[];
  };

  interface Props {
    rows: Row[];
    height?: number;
  }

  let { rows, height = 220 }: Props = $props();

  let container: HTMLDivElement | undefined = $state();
  let vegaEmbed: any = null;
  let view: any = null;

  $effect(() => {
    if (!container || vegaEmbed) return;
    (async () => {
      const mod = await import("vega-embed");
      vegaEmbed = mod.default ?? mod;
      render();
    })();
  });

  $effect(() => {
    void rows;
    if (!vegaEmbed || !container) return;
    render();
  });

  function render() {
    if (!container || !vegaEmbed) return;
    const chrome = chartChrome();
    const tonePalette = tones();

    // Long-form: one row per (species, sigma) for the strip layer; the
    // median bars use a separate aggregated table per species so we
    // can colour them by species and click through.
    const stripData: Array<{ species: string; sigma: number }> = [];
    const medians: Array<{
      species: string;
      median_sigma: number;
      n_findings: number;
      total_trials: number;
      href: string;
    }> = [];
    for (const r of rows) {
      for (const s of r.sigmas) {
        if (Number.isFinite(s)) stripData.push({ species: r.species, sigma: s });
      }
      if (r.median_sigma !== null && Number.isFinite(r.median_sigma)) {
        medians.push({
          species: r.species,
          median_sigma: r.median_sigma,
          n_findings: r.n_findings,
          total_trials: r.total_trials,
          href: r.href,
        });
      }
    }

    const speciesOrder = [...rows]
      .sort((a, b) => (b.median_sigma ?? 0) - (a.median_sigma ?? 0))
      .map((r) => r.species);

    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height,
      layer: [
        {
          data: { values: stripData },
          mark: {
            type: "tick",
            thickness: 1.4,
            color: tonePalette.muted,
            opacity: 0.6,
          },
          encoding: {
            x: {
              field: "sigma",
              type: "quantitative",
              title: "Slope σ (lower = steeper)",
            },
            y: {
              field: "species",
              type: "nominal",
              sort: speciesOrder,
              title: null,
            },
          },
        },
        {
          data: { values: medians },
          mark: {
            type: "point",
            filled: true,
            size: 180,
            opacity: 1,
          },
          encoding: {
            x: { field: "median_sigma", type: "quantitative" },
            y: {
              field: "species",
              type: "nominal",
              sort: speciesOrder,
            },
            color: {
              field: "species",
              type: "nominal",
              scale: { scheme: "tableau10" },
              legend: null,
            },
            href: { field: "href", type: "nominal" },
            tooltip: [
              { field: "species", title: "Species" },
              { field: "median_sigma", title: "Median σ", format: ".3f" },
              { field: "n_findings", title: "Findings" },
              { field: "total_trials", title: "Σ trials", format: "," },
            ],
          },
        },
      ],
      config: {
        view: { stroke: chrome.viewStroke },
        axis: {
          gridColor: chrome.gridColor,
          labelColor: chrome.labelColor,
          titleColor: chrome.titleColor,
        },
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
        console.error("AggregateBySpecies vega-embed failed", err);
      }
    })();
  }
</script>

{#if rows.length === 0}
  <p class="text-body-xs text-fg-muted">No species rows.</p>
{:else}
  <div bind:this={container} class="w-full"></div>
  <p class="mt-2 text-mono-id text-fg-muted">
    Filled point is the median σ; light tick marks are the per-finding
    distribution. Click a median to open the species' findings.
  </p>
{/if}
