<!--
  LiveFitHero — first-paint demo of the atlas's killer feature.

  Shows one curated psychometric on the left and, on the right, a
  primary CTA that loads Pyodide + scipy in the browser and refits a
  4-parameter logistic in real time. Once Pyodide is warm, subsequent
  refits are instant. The fitted curve animates onto the chart and
  the parameters slide in beside it.

  Pyodide is *not* preloaded — a 10 MB download on every first paint
  would be hostile. Loading begins on the user's first click; the
  CTA's label switches through "Loading Pyodide…" → "Fitting…" →
  "Refit again" so the user always knows where they are.
-->
<script lang="ts">
  import { chartChrome, tones } from "../lib/encoding";

  type Point = {
    x: number;
    y: number;
    n: number;
    y_lower?: number | null;
    y_upper?: number | null;
  };

  type FitParams = {
    mu: number;
    sigma: number;
    gamma: number;
    lapse: number;
    threshold: number | null;
  };

  type FitLine = Array<{ x: number; y: number }>;

  interface Props {
    findingId: string;
    paperCitation: string;
    species: string | null;
    nTrials: number | null;
    xLabel: string;
    xUnits: string | null;
    yLabel: string;
    points: Point[];
    findingHref: string;
  }

  let {
    findingId,
    paperCitation,
    species,
    nTrials,
    xLabel,
    xUnits,
    yLabel,
    points,
    findingHref,
  }: Props = $props();

  type Status = "cold" | "loading-runtime" | "loading-packages" | "fitting" | "done" | "error";

  let status = $state<Status>("cold");
  let errorMessage = $state("");
  let fitParams = $state<FitParams | null>(null);
  let fitLine = $state<FitLine>([]);
  let runCount = $state(0);

  let pyodide: any = null;
  let pyodidePromise: Promise<any> | null = null;

  const PYODIDE_VERSION = "0.26.4";
  const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

  const FIT_PYTHON = `
import json as _hero_json
import numpy as np
from scipy import optimize


def _logistic4(x, mu, sigma, gamma, lapse):
    sig = max(float(sigma), 1e-6)
    return gamma + (1 - gamma - lapse) / (1 + np.exp(-(x - mu) / sig))


def hero_fit(payload_json):
    payload = _hero_json.loads(payload_json)
    pts = payload["points"]
    if len(pts) < 4:
        return _hero_json.dumps({"params": None, "line": []})
    xs = np.array([p["x"] for p in pts], dtype=float)
    ys = np.array([p["y"] for p in pts], dtype=float)
    ns = np.array([max(p.get("n", 1), 1) for p in pts], dtype=float)
    sigma_weight = 1.0 / np.sqrt(ns)
    mu0 = float(np.mean(xs))
    span = float(np.max(xs) - np.min(xs)) or 1.0
    sigma0 = max(span / 4.0, 1e-3)
    try:
        popt, _ = optimize.curve_fit(
            _logistic4, xs, ys,
            p0=[mu0, sigma0, 0.05, 0.05],
            sigma=sigma_weight, absolute_sigma=False,
            bounds=([-np.inf, 1e-3, 0.0, 0.0], [np.inf, np.inf, 0.49, 0.49]),
            maxfev=4000,
        )
        mu, sigma, gamma, lapse = popt
        params = {
            "mu": float(mu),
            "sigma": float(sigma),
            "gamma": float(gamma),
            "lapse": float(lapse),
        }
    except Exception as exc:  # noqa: BLE001
        return _hero_json.dumps({"params": None, "line": [], "error": str(exc)})

    target_y = float(payload.get("target_y", 0.75))
    span_total = 1.0 - params["gamma"] - params["lapse"]
    threshold = None
    if span_total > 0:
        z = (target_y - params["gamma"]) / span_total
        if 0 < z < 1:
            sig = max(params["sigma"], 1e-6)
            threshold = float(params["mu"] - sig * np.log((1.0 - z) / z))
    params["threshold"] = threshold

    grid = np.linspace(float(np.min(xs)), float(np.max(xs)), 100)
    line_ys = _logistic4(grid, params["mu"], params["sigma"], params["gamma"], params["lapse"])
    line = [{"x": float(x), "y": float(y)} for x, y in zip(grid.tolist(), line_ys.tolist())]
    return _hero_json.dumps({"params": params, "line": line})
`;

  async function ensurePyodide(): Promise<any> {
    if (pyodide) return pyodide;
    if (pyodidePromise) return pyodidePromise;
    status = "loading-runtime";
    pyodidePromise = (async () => {
      const scriptId = "pyodide-cdn-script";
      if (typeof document !== "undefined" && !document.getElementById(scriptId)) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement("script");
          script.id = scriptId;
          script.src = `${PYODIDE_BASE}pyodide.js`;
          script.async = true;
          script.onload = () => resolve();
          script.onerror = () => reject(new Error("Failed to load Pyodide"));
          document.head.appendChild(script);
        });
      }
      const w: any = window;
      const py = await w.loadPyodide({ indexURL: PYODIDE_BASE });
      status = "loading-packages";
      await py.loadPackage(["numpy", "scipy"]);
      await py.runPythonAsync(FIT_PYTHON);
      pyodide = py;
      return py;
    })();
    return pyodidePromise;
  }

  async function refit() {
    errorMessage = "";
    try {
      const py = await ensurePyodide();
      status = "fitting";
      const targetY = 0.75;
      const payload = JSON.stringify({
        points: points.map((p) => ({ x: p.x, y: p.y, n: p.n })),
        target_y: targetY,
      });
      py.globals.set("_hero_payload", payload);
      const raw: any = await py.runPythonAsync("hero_fit(_hero_payload)");
      const json = String(raw ?? "{}");
      raw?.destroy?.();
      const parsed = JSON.parse(json);
      if (parsed.error) {
        throw new Error(parsed.error);
      }
      fitParams = parsed.params;
      fitLine = parsed.line ?? [];
      runCount += 1;
      status = "done";
    } catch (err) {
      errorMessage = err instanceof Error ? err.message : String(err);
      status = "error";
    }
  }

  // Vega-Lite chart with observed points + Wilson CI rules + fitted line.
  // Re-renders whenever the fit data changes; the fit-line layer fades in
  // via the chart's own redraw rather than a CSS transition (Vega's view
  // mount handles the visual swap).
  let chartContainer: HTMLDivElement | undefined = $state();
  let vegaEmbed: any = null;
  let chartReady = $state(false);
  let chartView: any = null;

  function wilson(p: number, n: number): { lower: number; upper: number } | null {
    if (!Number.isFinite(p) || !Number.isFinite(n) || n <= 0) return null;
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

  const observedRows = $derived(
    points.map((p) => {
      const ci = wilson(p.y, p.n);
      return {
        x: p.x,
        y: p.y,
        n: p.n,
        y_lower: ci?.lower ?? null,
        y_upper: ci?.upper ?? null,
      };
    }),
  );

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
    const tonePalette = tones();
    const xTitle = xUnits ? `${xLabel} (${xUnits})` : xLabel;
    const layers: Record<string, unknown>[] = [
      // Wilson CI rules behind the line.
      {
        data: { values: observedRows },
        transform: [
          {
            filter:
              "isValid(datum.y_lower) && isValid(datum.y_upper) && datum.y_lower !== datum.y_upper",
          },
        ],
        mark: { type: "rule", strokeWidth: 1.4, opacity: 0.45, color: tonePalette.muted },
        encoding: {
          x: { field: "x", type: "quantitative" },
          y: { field: "y_lower", type: "quantitative" },
          y2: { field: "y_upper" },
        },
      },
      // Observed points.
      {
        data: { values: observedRows },
        mark: { type: "point", filled: true, size: 80, opacity: 0.85, color: tonePalette.primary },
        encoding: {
          x: { field: "x", type: "quantitative", title: xTitle },
          y: {
            field: "y",
            type: "quantitative",
            title: yLabel,
            scale: { domain: [0, 1] },
          },
          tooltip: [
            { field: "x", title: xTitle, format: ".3f" },
            { field: "y", title: yLabel, format: ".3f" },
            { field: "n", title: "n" },
          ],
        },
      },
    ];
    if (fitLine.length > 0) {
      layers.push({
        data: { values: fitLine },
        mark: {
          type: "line",
          interpolate: "monotone",
          strokeWidth: 3,
          color: tonePalette.accent,
        },
        encoding: {
          x: { field: "x", type: "quantitative" },
          y: { field: "y", type: "quantitative" },
        },
      });
    }
    const spec = {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      width: "container" as const,
      height: 300,
      layer: layers,
      config: {
        view: { stroke: chrome.viewStroke },
        axis: { gridColor: chrome.gridColor, labelColor: chrome.labelColor },
        legend: { disable: true } as Record<string, unknown>,
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
        console.error("LiveFitHero vega-embed failed", err);
      }
    })();
  });

  const ctaLabel = $derived.by(() => {
    if (status === "loading-runtime") return "Loading Pyodide…";
    if (status === "loading-packages") return "Loading numpy + scipy…";
    if (status === "fitting") return "Fitting…";
    if (status === "done") return runCount > 1 ? `Refit again (${runCount}×)` : "Refit again";
    if (status === "error") return "Try again";
    return "Refit live in your browser";
  });

  const ctaWorking = $derived(
    status === "loading-runtime" || status === "loading-packages" || status === "fitting",
  );

  function fmt(v: number | null | undefined, digits = 3): string {
    if (v === null || v === undefined || !Number.isFinite(v)) return "—";
    return v.toFixed(digits);
  }

  const trialsLabel = $derived.by(() => {
    if (typeof nTrials !== "number" || !Number.isFinite(nTrials) || nTrials <= 0)
      return null;
    return `${nTrials.toLocaleString()} trials`;
  });
</script>

<section
  class="overflow-hidden rounded-md border border-rule bg-surface-raised"
  aria-labelledby="live-fit-hero-title"
>
  <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
    <div class="border-b border-rule p-5 lg:border-b-0 lg:border-r">
      <p class="text-eyebrow uppercase text-accent">Live demo</p>
      <h2 id="live-fit-hero-title" class="mt-1 text-h3 text-fg">
        Refit a curated psychometric, in your browser
      </h2>
      <p class="mt-2 max-w-prose text-body text-fg-secondary">
        The atlas runs Pyodide + scipy locally and fits a 4-parameter
        logistic to <span class="font-mono text-fg">{points.length}</span>
        observed points{trialsLabel ? ` (${trialsLabel})` : ""} from
        <a class="text-accent" href={findingHref}>{paperCitation.split(".")[0]}</a>.
        First click downloads ~10 MB of runtime; subsequent fits are
        instant.
      </p>
      <div class="mt-4 -mx-1 overflow-x-auto px-1">
        <div bind:this={chartContainer} class="min-w-[360px]"></div>
      </div>
      <p class="mt-2 text-mono-id text-fg-muted">
        Bars are Wilson 95% CIs from each point's <code>n</code>.
        {fitLine.length > 0 ? "Accent line is the live fit." : ""}
      </p>
    </div>
    <div class="flex flex-col gap-3 p-5">
      <button
        type="button"
        class={[
          "inline-flex items-center justify-center gap-2 rounded-md border px-4 py-2 text-body font-semibold transition-colors",
          ctaWorking
            ? "border-accent bg-accent-soft text-accent"
            : status === "done"
              ? "border-accent bg-accent text-fg-inverse hover:opacity-90"
              : "border-accent bg-accent text-fg-inverse hover:opacity-90",
        ]}
        onclick={refit}
        disabled={ctaWorking}
        aria-live="polite"
      >
        {#if ctaWorking}
          <span
            class="inline-block h-2 w-2 animate-pulse rounded-full bg-accent"
            aria-hidden="true"
          ></span>
        {:else}
          <span aria-hidden="true">{status === "done" ? "↻" : "▶"}</span>
        {/if}
        <span>{ctaLabel}</span>
      </button>

      <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-body-xs">
        <div>
          <dt class="text-eyebrow uppercase text-fg-muted">Species</dt>
          <dd class="mt-0.5 text-fg">{species ?? "—"}</dd>
        </div>
        <div>
          <dt class="text-eyebrow uppercase text-fg-muted">Trials</dt>
          <dd class="mt-0.5 font-mono text-fg">{trialsLabel ?? "—"}</dd>
        </div>
      </dl>

      {#if fitParams}
        <div class="animate-fade-in rounded-md border border-rule bg-surface p-3">
          <p class="mb-2 text-eyebrow uppercase text-fg-muted">
            Live fit parameters
          </p>
          <dl class="grid grid-cols-2 gap-x-3 gap-y-1.5 text-body-xs">
            <dt class="font-mono text-fg-muted">μ (bias)</dt>
            <dd class="text-right font-mono text-fg">{fmt(fitParams.mu)}</dd>
            <dt class="font-mono text-fg-muted">σ (slope)</dt>
            <dd class="text-right font-mono text-fg">{fmt(fitParams.sigma)}</dd>
            <dt class="font-mono text-fg-muted">γ (lower lapse)</dt>
            <dd class="text-right font-mono text-fg">{fmt(fitParams.gamma)}</dd>
            <dt class="font-mono text-fg-muted">λ (upper lapse)</dt>
            <dd class="text-right font-mono text-fg">{fmt(fitParams.lapse)}</dd>
            <dt class="font-mono text-fg-muted">x at 75%</dt>
            <dd class="text-right font-mono text-fg">{fmt(fitParams.threshold)}</dd>
          </dl>
        </div>
      {:else}
        <div class="rounded-md border border-dashed border-rule p-3 text-body-xs text-fg-muted">
          Click <span class="font-semibold">Refit live</span> to run a 4-parameter
          logistic on this curve in your browser. Parameters appear here once
          the fit completes.
        </div>
      {/if}

      {#if status === "error"}
        <p class="rounded border border-bad bg-bad-soft px-2 py-1 text-body-xs text-bad">
          Fit failed: {errorMessage}
        </p>
      {/if}

      <p class="mt-auto text-mono-id text-fg-muted">
        Same Python that runs the build-time fits — the page just delegates
        to your machine. <a class="text-accent" href={findingHref}>Open
        finding {findingId.replace("finding.", "")}</a>
        for diagnostics, residuals, and the full fit table.
      </p>
    </div>
  </div>
</section>
