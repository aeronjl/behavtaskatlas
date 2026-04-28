<script lang="ts">
  import { EditorState } from "@codemirror/state";
  import { EditorView, keymap } from "@codemirror/view";
  import { python, pythonLanguage } from "@codemirror/lang-python";
  import {
    type Completion,
    type CompletionContext,
  } from "@codemirror/autocomplete";
  import { basicSetup } from "codemirror";

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
  let svgOutput: string | null = $state(null);
  let errorMessage: string = $state("");
  let elapsedMs: number | null = $state(null);
  let currentSnippet: string = $state(pythonSnippet);
  let edited = $derived(currentSnippet !== pythonSnippet);

  let editorContainer: HTMLDivElement | undefined = $state();
  let editorView: EditorView | null = null;

  // Column names from the CSV header, populated after the first successful
  // fetch. Drives the df["…"] column autocomplete.
  let csvColumns: string[] = $state([]);

  const PANDAS_API: Completion[] = [
    { label: "DataFrame", type: "class" },
    { label: "Series", type: "class" },
    { label: "read_csv", type: "function" },
    { label: "to_numeric", type: "function" },
    { label: "to_datetime", type: "function" },
    { label: "concat", type: "function" },
    { label: "merge", type: "function" },
  ].map((c) => ({ ...c, label: `pd.${c.label}` }));

  const NUMPY_API: Completion[] = [
    "array",
    "asarray",
    "arange",
    "linspace",
    "where",
    "mean",
    "median",
    "std",
    "var",
    "min",
    "max",
    "isnan",
    "nan",
    "log",
    "log2",
    "log10",
    "exp",
    "sqrt",
    "abs",
  ].map((name) => ({ label: `np.${name}`, type: "function" }));

  const PLT_API: Completion[] = [
    "subplots",
    "plot",
    "scatter",
    "hist",
    "bar",
    "errorbar",
    "axhline",
    "axvline",
    "xlabel",
    "ylabel",
    "title",
    "legend",
    "grid",
    "figure",
    "show",
    "savefig",
  ].map((name) => ({ label: `plt.${name}`, type: "function" }));

  const DATAFRAME_METHODS: Completion[] = [
    "head",
    "tail",
    "shape",
    "columns",
    "index",
    "dtypes",
    "describe",
    "info",
    "groupby",
    "pivot",
    "pivot_table",
    "merge",
    "apply",
    "map",
    "mean",
    "median",
    "sum",
    "count",
    "min",
    "max",
    "std",
    "var",
    "value_counts",
    "unique",
    "nunique",
    "dropna",
    "fillna",
    "astype",
    "loc",
    "iloc",
    "to_string",
    "to_dict",
    "query",
    "sort_values",
    "reset_index",
    "set_index",
    "isin",
    "round",
  ].map((name) => ({ label: name, type: "method" }));

  const STATIC_API_COMPLETIONS: Completion[] = [
    ...PANDAS_API,
    ...NUMPY_API,
    ...PLT_API,
    ...DATAFRAME_METHODS,
  ];

  function pythonCompletions(context: CompletionContext) {
    const line = context.state.doc.lineAt(context.pos);
    const before = line.text.slice(0, context.pos - line.from);

    // df["..." | df['...' — column name autocomplete from the CSV header.
    const colMatch = before.match(/df\[\s*["']([^"']*)$/);
    if (colMatch && csvColumns.length > 0) {
      const partial = colMatch[1];
      return {
        from: context.pos - partial.length,
        options: csvColumns.map((col) => ({
          label: col,
          type: "property",
          boost: 1,
        })),
        validFor: /^[\w\- ]*$/,
      };
    }

    // Otherwise, identifier completion using the static pandas/numpy/matplotlib
    // API list.
    const word = context.matchBefore(/[\w.]+/);
    if (!word || (word.from === word.to && !context.explicit)) return null;
    return {
      from: word.from,
      options: STATIC_API_COMPLETIONS,
      validFor: /^[\w.]*$/,
    };
  }

  const pythonCompletionExtension = pythonLanguage.data.of({
    autocomplete: pythonCompletions,
  });

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

  $effect(() => {
    if (!editorContainer || editorView) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: currentSnippet,
        extensions: [
          basicSetup,
          python(),
          pythonCompletionExtension,
          keymap.of([
            {
              key: "Mod-Enter",
              preventDefault: true,
              run: () => {
                run();
                return true;
              },
            },
          ]),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              currentSnippet = update.state.doc.toString();
            }
          }),
          EditorView.theme({
            "&": { fontSize: "12px" },
            ".cm-content": {
              fontFamily:
                "ui-monospace, SFMono-Regular, 'Menlo', 'Monaco', monospace",
              padding: "8px 0",
            },
            ".cm-gutters": { backgroundColor: "#f8fafc" },
            ".cm-focused": { outline: "none" },
          }),
        ],
      }),
      parent: editorContainer,
    });
    editorView = view;
    return () => {
      view.destroy();
      editorView = null;
    };
  });

  function resetSnippet() {
    currentSnippet = pythonSnippet;
    if (editorView) {
      editorView.dispatch({
        changes: {
          from: 0,
          to: editorView.state.doc.length,
          insert: pythonSnippet,
        },
      });
    }
  }

  // Persist user edits to sessionStorage so an accidental reload does not
  // throw away in-progress work. We use sessionStorage rather than
  // localStorage so a fresh visit on another day picks up the latest default
  // snippet from the page rather than a possibly stale saved version.
  const sessionKey = `behavtaskatlas:snippet:${trialsUrl}`;

  $effect(() => {
    if (typeof sessionStorage === "undefined") return;
    const saved = sessionStorage.getItem(sessionKey);
    if (saved === null || saved === currentSnippet) return;
    currentSnippet = saved;
    if (editorView) {
      editorView.dispatch({
        changes: {
          from: 0,
          to: editorView.state.doc.length,
          insert: saved,
        },
      });
    }
  });

  $effect(() => {
    if (typeof sessionStorage === "undefined") return;
    if (currentSnippet === pythonSnippet) {
      sessionStorage.removeItem(sessionKey);
    } else {
      sessionStorage.setItem(sessionKey, currentSnippet);
    }
  });

  function indentSnippet(snippet: string): string {
    return snippet
      .split("\n")
      .map((line) => "    " + line)
      .join("\n");
  }

  async function run() {
    output = "";
    svgOutput = null;
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

      // First line of the CSV is the column header; expose it for the
      // df["…"] autocomplete.
      const headerLine = csvText.split(/\r?\n/, 1)[0] ?? "";
      if (headerLine) {
        csvColumns = headerLine.split(",").map((col) => col.trim());
      }
      status = "loading-packages";
      await py.loadPackagesFromImports(currentSnippet);
      status = "running";
      const wrapped = `
import sys, io, json
import pandas as pd
_buf = io.StringIO()
_orig = sys.stdout
sys.stdout = _buf
_svg = None

# If matplotlib is loaded, capture plt.show() into _svg.
try:
    import matplotlib as _mpl
    _mpl.use("Agg")
    import matplotlib.pyplot as _plt
    def _capture_show(*args, **kwargs):
        global _svg
        fig = _plt.gcf()
        buf = io.StringIO()
        fig.savefig(buf, format="svg", bbox_inches="tight")
        _svg = buf.getvalue()
        _plt.close(fig)
    _plt.show = _capture_show
except ImportError:
    pass

try:
    df = pd.read_csv(io.StringIO(_csv_text))
    if "task_variables_json" in df.columns:
        df["task_variables"] = (
            df["task_variables_json"].fillna("{}").apply(json.loads)
        )
${indentSnippet(currentSnippet)}
finally:
    sys.stdout = _orig
{"stdout": _buf.getvalue(), "svg": _svg}
`.trim();
      const result: any = await py.runPythonAsync(wrapped);
      const obj = (result?.toJs?.({ dict_converter: Object.fromEntries }) ??
        result) as { stdout?: string; svg?: string | null };
      output = String(obj.stdout ?? "");
      svgOutput = obj.svg ? String(obj.svg) : null;
      result?.destroy?.();
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
  <div class="mb-3">
    <span class="mb-1 block text-xs font-medium text-slate-600"
      >Python (df is a pandas DataFrame loaded from the trials CSV;
      ⌘/Ctrl-Enter to run)</span
    >
    <div
      bind:this={editorContainer}
      class="overflow-hidden rounded border border-slate-200 bg-white"
    ></div>
  </div>
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
        onclick={resetSnippet}
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
  {#if svgOutput}
    <div
      class="mt-3 overflow-x-auto rounded border border-slate-200 bg-white p-3"
    >
      {@html svgOutput}
    </div>
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
