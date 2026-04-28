<script lang="ts">
  import type { FindingsIndex, FindingsEntry } from "../lib/findings";

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

  const allEntries: FindingsEntry[] = data.findings;
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

  let currentCurveType = $state(
    allCurveTypes.includes("psychometric") ? "psychometric" : allCurveTypes[0] ?? "psychometric",
  );
  let active = $state<Record<FilterKey, Set<string>>>({
    species: new Set(filterOptions.species),
    source_data_level: new Set(filterOptions.source_data_level),
    evidence_type: new Set(filterOptions.evidence_type),
    response_modality: new Set(filterOptions.response_modality),
  });
  let yearStart = $state(minYear);
  let yearEnd = $state(maxYear);
  let searchText = $state("");

  const filteredEntries = $derived.by(() => {
    const needle = searchText.trim().toLowerCase();
    return allEntries.filter((entry) => {
      if (entry.curve_type !== currentCurveType) return false;
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

  const flatPoints = $derived.by(() =>
    filteredEntries.flatMap((entry) =>
      entry.points.map((p) => ({
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
      }))
    )
  );

  const yLabel = $derived.by(() => {
    if (filteredEntries.length === 0) return "Y";
    return filteredEntries[0].y_label;
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
  }

  let chartContainer: HTMLDivElement | undefined = $state();
  let chartReady = $state(false);
  let vegaEmbed: any = null;
  let chartView: any = null;

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
  let fitData = $state<{
    perCurve: Array<{ finding_id: string; line: Array<{ x: number; y: number }>; params: Record<string, number> | null }>;
    pooled: { line: Array<{ x: number; y: number }>; ci_band: Array<{ x: number; y: number; lower: number; upper: number }> | null; params: Record<string, number> } | null;
    curveType: string;
    filterSignature: string;
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


def fit_curves(payload_json):
    payload = _fit_json.loads(payload_json)
    curves = payload["curves"]
    pin_lower = payload.get("pin_lower")
    n_boot = int(payload.get("n_bootstrap", 80))

    per_curve = []
    all_points = []
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
        per_curve.append({
            "finding_id": c["finding_id"],
            "params": params,
            "line": line,
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

    return _fit_json.dumps({"per_curve": per_curve, "pooled": pooled})
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
      ids: filteredEntries.map((e) => e.finding_id),
    }),
  );

  async function runFit() {
    fitError = "";
    if (filteredEntries.length === 0) {
      fitData = null;
      fitStatus = "done";
      return;
    }
    try {
      const py = await ensureFitRuntime();
      fitStatus = "fitting";
      const curves = filteredEntries.map((entry) => ({
        finding_id: entry.finding_id,
        points: entry.points.map((p) => ({ x: p.x, y: p.y, n: p.n })),
      }));
      const payload = JSON.stringify({
        curves,
        pin_lower: pinLowerFor(currentCurveType),
        n_bootstrap: 80,
      });
      py.globals.set("_fit_payload", payload);
      const result: any = await py.runPythonAsync("fit_curves(_fit_payload)");
      const json = String(result ?? "{}");
      result?.destroy?.();
      const parsed = JSON.parse(json);
      fitData = {
        perCurve: parsed.per_curve ?? [],
        pooled: parsed.pooled ?? null,
        curveType: currentCurveType,
        filterSignature: signature,
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
          filteredEntries.find((e) => e.finding_id === c.finding_id)?.paper_citation
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
    const xTitle = filteredEntries[0]?.x_label ?? "x";
    const layers: Record<string, unknown>[] = [];

    if (fitEnabled && POOLED_BAND_VALUES.length > 0) {
      layers.push({
        data: { values: POOLED_BAND_VALUES },
        mark: { type: "area", opacity: 0.18, color: "#0f172a" },
        encoding: {
          x: { field: "x", type: "quantitative" },
          y: { field: "lower", type: "quantitative" },
          y2: { field: "upper" },
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
        mark: { type: "line", color: "#0f172a", strokeWidth: 3 },
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
        view: { stroke: "#cbd5e1" },
        axis: { gridColor: "#e2e8f0", labelColor: "#334155" },
        legend: { labelColor: "#334155", titleColor: "#0f172a" },
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

<div class="rounded-md border border-slate-200 bg-white p-4">
  <div class="mb-4 flex flex-wrap items-center gap-2">
    <span class="text-xs font-semibold text-slate-700">Curve type:</span>
    {#each allCurveTypes as type (type)}
      <button
        type="button"
        class:list={[
          "rounded-md border px-2.5 py-1 text-xs",
          type === currentCurveType
            ? "border-accent bg-accent text-white"
            : "border-slate-300 text-slate-700 hover:bg-slate-50",
        ]}
        onclick={() => (currentCurveType = type)}
      >
        {type.replace(/_/g, " ")}
      </button>
    {/each}
    <button
      type="button"
      class="ml-auto rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50"
      onclick={resetFilters}
    >
      Reset filters
    </button>
  </div>

  <div class="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
    {#each Object.entries(filterOptions) as [key, values] (key)}
      <fieldset class="rounded border border-slate-200 p-3">
        <legend class="px-1 text-xs font-semibold text-slate-700">
          {filterLabels[key as FilterKey]}
        </legend>
        <div class="mt-1 flex flex-wrap gap-x-4 gap-y-1">
          {#each values as value (value)}
            <label class="flex items-center gap-1 text-xs text-slate-700">
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
    <fieldset class="rounded border border-slate-200 p-3">
      <legend class="px-1 text-xs font-semibold text-slate-700">Year range</legend>
      <div class="mt-1 flex items-center gap-2 text-xs text-slate-700">
        <input
          type="number"
          min={minYear}
          max={maxYear}
          bind:value={yearStart}
          class="w-20 rounded border border-slate-200 px-1 py-0.5"
        />
        <span>–</span>
        <input
          type="number"
          min={minYear}
          max={maxYear}
          bind:value={yearEnd}
          class="w-20 rounded border border-slate-200 px-1 py-0.5"
        />
        <span class="ml-2 text-[11px] text-slate-500">
          (atlas: {minYear}–{maxYear})
        </span>
      </div>
    </fieldset>
    <fieldset class="rounded border border-slate-200 p-3">
      <legend class="px-1 text-xs font-semibold text-slate-700">Search</legend>
      <input
        type="search"
        placeholder="paper / protocol / finding id…"
        bind:value={searchText}
        class="mt-1 w-full rounded border border-slate-200 px-2 py-1 text-xs"
      />
    </fieldset>
  </div>

  <div class="mb-2 flex flex-wrap items-center gap-3">
    <p class="text-xs text-slate-600">
      Showing {filteredEntries.length} of {allEntries.length} findings,
      {flatPoints.length} points.
    </p>
    <label class="ml-auto flex items-center gap-2 text-xs text-slate-700">
      <input type="checkbox" bind:checked={fitEnabled} />
      <span>
        Fit + aggregate
        <span class="text-[11px] text-slate-500">
          (per-curve logistic + pooled fit + bootstrap CI)
        </span>
      </span>
    </label>
    {#if fitStatusLabel}
      <span class="text-[11px] text-slate-500">{fitStatusLabel}</span>
    {/if}
  </div>

  <div bind:this={chartContainer} class="w-full"></div>

  <p class="mt-3 text-[11px] text-slate-500">
    Curves at different source-data levels are shown on shared axes for visual
    comparison; point shape encodes the source level. Values for figure-source-
    data findings should be read as published rather than as a complete raw
    behavioral export.
  </p>
</div>
