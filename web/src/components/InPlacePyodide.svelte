<script lang="ts">
  type Status =
    | "idle"
    | "loading-runtime"
    | "loading-packages"
    | "fetching"
    | "running"
    | "done"
    | "error";

  type Props = {
    title?: string;
    description?: string;
    trialsUrl: string;
    pythonSnippet: string;
  };

  let {
    title = "In-place analysis",
    description = "",
    trialsUrl,
    pythonSnippet,
  }: Props = $props();

  let status: Status = $state("idle");
  let output: string = $state("");
  let errorMessage: string = $state("");
  let elapsedMs: number | null = $state(null);
  let currentSnippet: string = $state(pythonSnippet);
  let edited = $derived(currentSnippet !== pythonSnippet);

  let pyodide: any = null;
  let pyodidePromise: Promise<any> | null = null;

  const PYODIDE_VERSION = "0.26.4";
  const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

  const STATUS_LABELS: Record<string, string> = {
    idle: "Click run to start",
    "loading-runtime": "Loading Pyodide runtime…",
    "loading-packages": "Loading Python packages…",
    fetching: "Fetching trials CSV…",
    running: "Running analysis…",
    done: "Done",
    error: "Error",
  };

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
          script.onerror = () =>
            reject(new Error("Failed to load Pyodide script from CDN"));
          document.head.appendChild(script);
        });
      }
      const w: any = window;
      if (typeof w.loadPyodide !== "function") {
        throw new Error("loadPyodide is not available on window");
      }
      const py = await w.loadPyodide({ indexURL: PYODIDE_BASE });
      status = "loading-packages";
      await py.loadPackage(["pandas"]);
      pyodide = py;
      return py;
    })();
    return pyodidePromise;
  }

  function indentSnippet(snippet: string): string {
    return snippet
      .split("\n")
      .map((line) => "    " + line)
      .join("\n");
  }

  async function run() {
    output = "";
    errorMessage = "";
    elapsedMs = null;
    const t0 =
      typeof performance !== "undefined" ? performance.now() : Date.now();
    try {
      const py: any = await ensurePyodide();
      status = "fetching";
      const response = await fetch(trialsUrl);
      if (!response.ok) {
        throw new Error(
          `Failed to fetch trials CSV (HTTP ${response.status}) from ${trialsUrl}`,
        );
      }
      const csvText = await response.text();
      py.globals.set("_csv_text", csvText);
      status = "loading-packages";
      await py.loadPackagesFromImports(currentSnippet);
      status = "running";
      const wrapped = `
import sys, io, json
import pandas as pd
_buf = io.StringIO()
_orig = sys.stdout
sys.stdout = _buf
try:
    df = pd.read_csv(io.StringIO(_csv_text))
    if "task_variables_json" in df.columns:
        df["task_variables"] = (
            df["task_variables_json"].fillna("{}").apply(json.loads)
        )
${indentSnippet(currentSnippet)}
finally:
    sys.stdout = _orig
_buf.getvalue()
`.trim();
      const result = await py.runPythonAsync(wrapped);
      output = String(result ?? "");
      const t1 =
        typeof performance !== "undefined" ? performance.now() : Date.now();
      elapsedMs = Math.round(t1 - t0);
      status = "done";
    } catch (err) {
      errorMessage = err instanceof Error ? err.message : String(err);
      status = "error";
    }
  }

  let inFlight = $derived(
    status === "loading-runtime" ||
      status === "loading-packages" ||
      status === "fetching" ||
      status === "running",
  );
</script>

<div class="rounded-md border border-slate-200 bg-white p-4">
  <header class="mb-2 flex items-baseline justify-between gap-2">
    <h3 class="text-sm font-semibold text-slate-700">{title}</h3>
    <span class="text-xs text-slate-500">Pyodide {PYODIDE_VERSION}</span>
  </header>
  {#if description}
    <p class="mb-3 text-sm text-slate-700">{description}</p>
  {/if}
  <label class="mb-3 block">
    <span class="mb-1 block text-xs font-medium text-slate-600"
      >Python (df is a pandas DataFrame loaded from the trials CSV)</span
    >
    <textarea
      class="block w-full rounded border border-slate-200 bg-slate-50 p-2 font-mono text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-accent"
      spellcheck="false"
      autocomplete="off"
      autocorrect="off"
      rows={Math.max(6, currentSnippet.split('\n').length + 1)}
      bind:value={currentSnippet}
    ></textarea>
  </label>
  <div class="flex flex-wrap items-center gap-3">
    <button
      type="button"
      class="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:cursor-wait disabled:opacity-60"
      onclick={run}
      disabled={inFlight}
    >
      Run analysis
    </button>
    {#if edited}
      <button
        type="button"
        class="rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-50"
        onclick={() => (currentSnippet = pythonSnippet)}
        disabled={inFlight}
      >
        Reset
      </button>
    {/if}
    <span class="text-xs text-slate-500">
      {STATUS_LABELS[status]}{elapsedMs !== null
        ? ` · ${elapsedMs} ms`
        : ""}{edited ? " · edited" : ""}
    </span>
  </div>
  {#if output}
    <pre
      class="mt-3 max-h-96 overflow-auto rounded border border-slate-200 bg-slate-50 p-3 text-xs text-slate-800">{output}</pre>
  {/if}
  {#if errorMessage}
    <p
      class="mt-3 rounded border border-warn bg-warn-soft p-3 text-xs text-warn"
    >
      {errorMessage}
    </p>
  {/if}
  <p class="mt-3 text-xs text-slate-500">
    Runs entirely in your browser. First click downloads ~10 MB of Pyodide and
    pandas; subsequent runs reuse the cached runtime.
  </p>
</div>
