/**
 * Runtime bridge between the CSS `@theme` tokens (defined in
 * styles/global.css) and the chart components (Vega-Lite, raw SVG).
 *
 * Chart components call these helpers when building specs. Each call
 * reads the current resolved value from `:root` via `getComputedStyle`,
 * with a hex fallback for SSR (where `window` doesn't exist) and for
 * environments where the variable isn't defined.
 *
 * Why this shape:
 * - `chartChrome()` covers axis, grid, view-stroke, label, title — the
 *   non-data colors that ought to match the rest of the UI.
 * - `sourceColors()`, `curveColors()`, `modelColors()`, `confidenceColors()`
 *   cover the four encoding axes the data-vis layer cares about.
 * - `tones()` exposes the status palette for callouts inside charts
 *   (disagreement bands, pooled-fit overlays, etc.).
 *
 * All helpers return fresh values each call — so a future dark-mode
 * toggle that swaps the underlying tokens propagates on the next
 * chart re-render.
 */

function readVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

export function chartChrome() {
  return {
    viewStroke: readVar("--color-rule-strong", "#cbd5e1"),
    gridColor: readVar("--color-rule", "#e2e8f0"),
    labelColor: readVar("--color-fg-secondary", "#334155"),
    titleColor: readVar("--color-fg", "#0f172a"),
    mutedFg: readVar("--color-fg-muted", "#64748b"),
    subtleFg: readVar("--color-fg-subtle", "#94a3b8"),
  };
}

export function sourceColors(): Record<string, string> {
  return {
    "raw-trial": readVar("--color-encoding-source-raw", "#10b981"),
    "processed-trial": readVar("--color-encoding-source-processed", "#0ea5e9"),
    "figure-source-data": readVar("--color-encoding-source-figure", "#f59e0b"),
  };
}

export function curveColors(): Record<string, string> {
  return {
    psychometric: readVar("--color-encoding-curve-psychometric", "#2563eb"),
    chronometric: readVar("--color-encoding-curve-chronometric", "#14b8a6"),
    accuracy_by_strength: readVar("--color-encoding-curve-accuracy", "#7c3aed"),
    hit_rate: readVar("--color-encoding-curve-hit-rate", "#f43f5e"),
  };
}

export function modelColors(): Record<string, string> {
  return {
    sdt: readVar("--color-encoding-model-sdt", "#0ea5e9"),
    ddm: readVar("--color-encoding-model-ddm", "#7c3aed"),
    logistic: readVar("--color-encoding-model-logistic", "#2563eb"),
    click: readVar("--color-encoding-model-click", "#f59e0b"),
    bernoulli: readVar("--color-encoding-model-bernoulli", "#64748b"),
    chronometric: readVar("--color-encoding-model-chronometric", "#14b8a6"),
  };
}

export function confidenceColors(): Record<string, string> {
  return {
    decisive: readVar("--color-confidence-decisive", "#047857"),
    supported: readVar("--color-confidence-supported", "#0d9488"),
    close: readVar("--color-confidence-close", "#d97706"),
    single_candidate: readVar("--color-confidence-single", "#94a3b8"),
  };
}

export function tones() {
  return {
    accent: readVar("--color-accent", "#2b5ea0"),
    warn: readVar("--color-warn", "#b35c00"),
    bad: readVar("--color-bad", "#9f2424"),
    ok: readVar("--color-ok", "#246b3b"),
    primary: readVar("--color-fg", "#0f172a"),
    muted: readVar("--color-fg-muted", "#64748b"),
  };
}
