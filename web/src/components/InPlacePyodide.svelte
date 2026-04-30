<script lang="ts">
  import { EditorState } from "@codemirror/state";
  import {
    EditorView,
    keymap,
    hoverTooltip,
    type Tooltip,
  } from "@codemirror/view";
  import { python, pythonLanguage } from "@codemirror/lang-python";
  import {
    type Completion,
    type CompletionContext,
  } from "@codemirror/autocomplete";
  import { linter, type Diagnostic } from "@codemirror/lint";
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

  // jedi-driven completion. Loaded lazily after Pyodide is up; until then,
  // the static API list + CSV columns are the completion source.
  let jediReady = $state(false);
  let jediLoadPromise: Promise<void> | null = null;

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

  // Match jedi's completion `type` strings to CodeMirror's icon palette so
  // results render with sensible icons in the autocomplete popup.
  const JEDI_TYPE_MAP: Record<string, string> = {
    function: "function",
    method: "method",
    class: "class",
    module: "namespace",
    param: "variable",
    instance: "variable",
    statement: "variable",
    property: "property",
    keyword: "keyword",
  };

  // Preamble we prepend before sending the snippet to jedi so it knows
  // pd, np, plt, and df without the user having to import them first.
  const JEDI_PREAMBLE = `import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
df: pd.DataFrame = pd.DataFrame()
`;
  const JEDI_PREAMBLE_LINES = JEDI_PREAMBLE.split("\n").length - 1;

  type Position = { line: number; column: number };

  function positionForPos(code: string, pos: number): Position {
    const before = code.slice(0, pos);
    const lines = before.split("\n");
    return {
      line: lines.length + JEDI_PREAMBLE_LINES,
      column: lines[lines.length - 1].length,
    };
  }

  async function callJedi(kind: string, code: string, position?: Position) {
    if (!pyodide) return null;
    const py = pyodide as {
      globals: { get: (name: string) => unknown };
    };
    const queryFn: any = py.globals.get("_lsp_query");
    if (typeof queryFn !== "function") return null;
    try {
      const result = await queryFn(
        kind,
        JEDI_PREAMBLE + code,
        position?.line ?? 0,
        position?.column ?? 0,
      );
      const text = typeof result === "string" ? result : String(result);
      result?.destroy?.();
      return JSON.parse(text);
    } catch {
      return null;
    }
  }

  async function jediCompletions(
    code: string,
    pos: number,
  ): Promise<Completion[]> {
    const parsed = await callJedi(
      "complete",
      code,
      positionForPos(code, pos),
    );
    if (!Array.isArray(parsed)) return [];
    return parsed.map((entry: { name: string; type?: string }) => ({
      label: entry.name,
      type:
        (entry.type && JEDI_TYPE_MAP[entry.type]) ??
        (entry.type ? "variable" : undefined),
    }));
  }

  async function jediHelp(
    code: string,
    pos: number,
  ): Promise<{ name: string; type?: string; doc?: string } | null> {
    const parsed = await callJedi("help", code, positionForPos(code, pos));
    if (!Array.isArray(parsed) || parsed.length === 0) return null;
    return parsed[0] ?? null;
  }

  type JediSyntaxError = {
    line: number;
    column: number;
    until_line: number;
    until_column: number;
    message: string;
  };

  async function jediSyntaxErrors(code: string): Promise<JediSyntaxError[]> {
    const parsed = await callJedi("errors", code);
    if (!Array.isArray(parsed)) return [];
    return parsed as JediSyntaxError[];
  }

  async function pythonCompletions(
    context: CompletionContext,
  ): Promise<{
    from: number;
    options: Completion[];
    validFor?: RegExp;
  } | null> {
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

    const word = context.matchBefore(/[\w.]+/);
    if (!word || (word.from === word.to && !context.explicit)) return null;

    if (jediReady) {
      try {
        const fullCode = context.state.doc.toString();
        const jediResults = await jediCompletions(fullCode, context.pos);
        if (jediResults.length > 0) {
          return {
            from: word.from,
            options: jediResults,
            validFor: /^[\w.]*$/,
          };
        }
      } catch {
        // Fall through to static completions on jedi failure.
      }
    }

    return {
      from: word.from,
      options: STATIC_API_COMPLETIONS,
      validFor: /^[\w.]*$/,
    };
  }

  const pythonCompletionExtension = pythonLanguage.data.of({
    autocomplete: pythonCompletions,
  });

  const pythonHoverExtension = hoverTooltip(
    async (view, pos): Promise<Tooltip | null> => {
      if (!jediReady) return null;
      const code = view.state.doc.toString();
      const help = await jediHelp(code, pos);
      if (!help || (!help.doc && !help.type)) return null;
      return {
        pos,
        end: pos,
        above: true,
        create() {
          const dom = document.createElement("div");
          dom.className = "in-place-hover";
          const title = document.createElement("div");
          title.className = "in-place-hover-title";
          title.textContent = help.type
            ? `${help.name} (${help.type})`
            : help.name;
          dom.appendChild(title);
          if (help.doc) {
            const body = document.createElement("pre");
            body.className = "in-place-hover-body";
            body.textContent = help.doc;
            dom.appendChild(body);
          }
          return { dom };
        },
      };
    },
    { hoverTime: 350 },
  );

  function lineColToPos(state: EditorState, line: number, col: number): number {
    const totalLines = state.doc.lines;
    const safeLine = Math.max(1, Math.min(totalLines, line));
    const lineInfo = state.doc.line(safeLine);
    return Math.max(lineInfo.from, Math.min(lineInfo.to, lineInfo.from + col));
  }

  const pythonLinterExtension = linter(async (view) => {
    if (!jediReady) return [];
    const code = view.state.doc.toString();
    const errors = await jediSyntaxErrors(code);
    const diagnostics: Diagnostic[] = [];
    for (const err of errors) {
      const startLine = err.line - JEDI_PREAMBLE_LINES;
      const endLine = err.until_line - JEDI_PREAMBLE_LINES;
      if (startLine < 1) continue; // error inside the preamble; not the user's
      const from = lineColToPos(view.state, startLine, err.column);
      const to = Math.max(
        from + 1,
        lineColToPos(view.state, endLine, err.until_column),
      );
      diagnostics.push({
        from,
        to,
        severity: "error",
        message: err.message,
      });
    }
    return diagnostics;
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
          pythonHoverExtension,
          pythonLinterExtension,
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
      ensureJedi();
    } catch (err) {
      errorMessage = err instanceof Error ? err.message : String(err);
      status = "error";
    }
  }

  // Load jedi in the background after the first successful Run, when Pyodide
  // is already up. Type-aware completions, hover docs, and syntax-error
  // linting all kick in once this resolves.
  function ensureJedi() {
    if (jediReady || jediLoadPromise || !pyodide) return;
    jediLoadPromise = (async () => {
      try {
        const py = pyodide as {
          loadPackage: (pkgs: string[]) => Promise<void>;
          runPythonAsync: (code: string) => Promise<unknown>;
        };
        await py.loadPackage(["jedi"]);
        // Define a single _lsp_query function so completion / hover / lint
        // calls don't fight over shared globals.
        await py.runPythonAsync(`
import jedi as _jedi
import json as _lsp_json

def _lsp_query(kind, code, line, col):
    script = _jedi.Script(code)
    if kind == "complete":
        items = script.complete(line, col)
        return _lsp_json.dumps([
            {"name": c.name, "type": c.type} for c in items[:80]
        ])
    if kind == "help":
        defs = script.help(line, col)
        return _lsp_json.dumps([
            {"name": d.name, "type": d.type, "doc": d.docstring()}
            for d in defs[:1]
        ])
    if kind == "errors":
        errors = script.get_syntax_errors()
        return _lsp_json.dumps([
            {
                "line": e.line,
                "column": e.column,
                "until_line": e.until_line,
                "until_column": e.until_column,
                "message": str(e),
            }
            for e in errors
        ])
    return "[]"
`);
        jediReady = true;
      } catch {
        // Soft fail; static completions remain available.
      }
    })();
  }

  let inFlight = $derived(
    status === "loading-runtime" ||
      status === "loading-packages" ||
      status === "fetching" ||
      status === "running",
  );
</script>

<div class="rounded-md border border-rule bg-surface-raised p-4">
  <header class="mb-2 flex items-baseline justify-between gap-2">
    <h3 class="text-sm font-semibold text-fg-secondary">{title}</h3>
    <span class="text-xs text-fg-muted">Pyodide {PYODIDE_VERSION}</span>
  </header>
  {#if description}
    <p class="mb-3 text-sm text-fg-secondary">{description}</p>
  {/if}
  <div class="mb-3">
    <span class="mb-1 block text-xs font-medium text-fg-muted"
      >Python (df is a pandas DataFrame loaded from the trials CSV;
      ⌘/Ctrl-Enter to run)</span
    >
    <div
      bind:this={editorContainer}
      class="overflow-hidden rounded border border-rule bg-surface-raised"
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
        class="rounded-md border border-rule-strong px-2.5 py-1 text-xs text-fg-secondary hover:bg-surface"
        onclick={resetSnippet}
        disabled={inFlight}
      >
        Reset
      </button>
    {/if}
    <span class="text-xs text-fg-muted">
      {STATUS_LABELS[status]}{elapsedMs !== null
        ? ` · ${elapsedMs} ms`
        : ""}{edited ? " · edited" : ""}
    </span>
  </div>

  {#if inFlight}
    <div
      class="mt-3 flex items-center gap-3 rounded border border-accent-soft bg-accent-soft px-3 py-2 text-xs text-accent"
      role="status"
      aria-live="polite"
    >
      <span
        class="inline-block h-2 w-2 animate-pulse rounded-full bg-accent"
        aria-hidden="true"
      ></span>
      <span>
        {STATUS_LABELS[status]}
        {#if status === "loading-runtime"}
          <span class="text-fg-muted">— first run downloads ~10 MB; subsequent runs are instant</span>
        {:else if status === "loading-packages"}
          <span class="text-fg-muted">— numpy, pandas, matplotlib (cached after first run)</span>
        {/if}
      </span>
    </div>
  {/if}
  {#if output}
    <pre
      class="mt-3 max-h-96 overflow-auto rounded border border-rule bg-surface p-3 text-xs text-fg">{output}</pre>
  {/if}
  {#if svgOutput}
    <div
      class="mt-3 overflow-x-auto rounded border border-rule bg-surface-raised p-3"
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
  <p class="mt-3 text-xs text-fg-muted">
    Runs entirely in your browser. First click downloads ~10 MB of Pyodide and
    pandas; subsequent runs reuse the cached runtime.
  </p>
</div>

<style>
  :global(.in-place-hover) {
    max-width: 540px;
    border: 1px solid #cbd5e1;
    background: white;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08);
    padding: 8px 10px;
    border-radius: 4px;
    font-size: 12px;
    color: #0f172a;
  }
  :global(.in-place-hover-title) {
    font-weight: 600;
    margin-bottom: 4px;
  }
  :global(.in-place-hover-body) {
    margin: 0;
    max-height: 220px;
    overflow: auto;
    white-space: pre-wrap;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
    font-size: 11px;
    line-height: 1.4;
    color: #334155;
  }
</style>
