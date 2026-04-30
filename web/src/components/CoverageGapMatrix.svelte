<script lang="ts">
  type GapView = "ready" | "blocked" | "extraction";
  type CellState = "ok" | "partial" | "ready" | "missing" | "blocked" | "unknown" | "na";

  type MatrixCellKey =
    | "raw_data"
    | "trial_table"
    | "figure_source"
    | "findings"
    | "model_fits"
    | "reports"
    | "source_request";

  type CoverageGapRow = {
    blocker: string;
    cells: Record<MatrixCellKey, CellState>;
    chips: string[];
    detail?: string | null;
    href: string;
    id: string;
    next_action: string;
    priority: string;
    request_href?: string | null;
    request_label?: string | null;
    source: string;
    status: string;
    target_id: string;
    target_label: string;
    target_type: string;
    view: GapView;
  };

  let { rows }: { rows: CoverageGapRow[] } = $props();

  const views: Array<{ value: "all" | GapView; label: string }> = [
    { value: "all", label: "All gaps" },
    { value: "ready", label: "Ready to implement" },
    { value: "blocked", label: "Blocked external data" },
    { value: "extraction", label: "Needs extraction" },
  ];

  const columns: Array<{ key: MatrixCellKey; label: string; title: string }> = [
    { key: "raw_data", label: "Raw", title: "raw data available" },
    { key: "trial_table", label: "Trials", title: "canonical trial table" },
    { key: "figure_source", label: "Figure", title: "figure source data" },
    { key: "findings", label: "Findings", title: "extracted findings" },
    { key: "model_fits", label: "Models", title: "model fits or model-ready target" },
    { key: "reports", label: "Reports", title: "report-backed vertical slice" },
    { key: "source_request", label: "Request", title: "DOI or source-data request state" },
  ];

  let view = $state<"all" | GapView>("all");
  let query = $state("");

  const queryTokens = $derived(
    query
      .toLowerCase()
      .split(/\s+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0),
  );

  function readable(value: string | null | undefined): string {
    if (!value) return "-";
    return value.replace(/[_-]/g, " ");
  }

  function priorityRank(value: string): number {
    if (value === "high") return 0;
    if (value === "medium" || value === "normal") return 1;
    if (value === "low") return 2;
    return 3;
  }

  function viewRank(value: GapView): number {
    if (value === "blocked") return 0;
    if (value === "ready") return 1;
    return 2;
  }

  function rowText(row: CoverageGapRow): string {
    return [
      row.id,
      row.target_id,
      row.target_label,
      row.target_type,
      row.priority,
      row.status,
      row.source,
      row.blocker,
      row.next_action,
      row.detail,
      ...row.chips,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
  }

  function rowMatches(row: CoverageGapRow): boolean {
    if (view !== "all" && row.view !== view) return false;
    if (queryTokens.length === 0) return true;
    const haystack = rowText(row);
    return queryTokens.every((token) => haystack.includes(token));
  }

  const filteredRows = $derived.by(() =>
    rows
      .filter(rowMatches)
      .sort(
        (a, b) =>
          priorityRank(a.priority) - priorityRank(b.priority) ||
          viewRank(a.view) - viewRank(b.view) ||
          a.target_label.localeCompare(b.target_label),
      ),
  );

  function viewCount(value: "all" | GapView): number {
    if (value === "all") return rows.length;
    return rows.filter((row) => row.view === value).length;
  }

  function viewLabel(value: GapView): string {
    if (value === "ready") return "ready";
    if (value === "blocked") return "blocked";
    return "extraction";
  }

  function viewClass(value: GapView): string {
    if (value === "ready") return "bg-ok-soft text-ok ring-ok/20";
    if (value === "blocked") return "bg-bad-soft text-bad ring-bad/20";
    return "bg-warn-soft text-warn ring-warn/20";
  }

  function priorityClass(value: string): string {
    if (value === "high") return "bg-warn-soft text-warn";
    if (value === "medium" || value === "normal") return "bg-accent-soft text-accent";
    return "bg-surface-sunken text-fg-muted";
  }

  function cellLabel(value: CellState): string {
    if (value === "ok") return "ok";
    if (value === "partial") return "part";
    if (value === "ready") return "ready";
    if (value === "missing") return "miss";
    if (value === "blocked") return "block";
    if (value === "na") return "n/a";
    return "unk";
  }

  function cellClass(value: CellState): string {
    if (value === "ok") return "bg-ok-soft text-ok ring-ok/20";
    if (value === "partial") return "bg-accent-soft text-accent ring-accent/20";
    if (value === "ready") return "bg-ok-soft text-ok ring-ok";
    if (value === "missing") return "bg-surface-sunken text-fg-muted ring-rule";
    if (value === "blocked") return "bg-bad-soft text-bad ring-bad/20";
    if (value === "na") return "bg-surface-raised text-fg-subtle ring-rule";
    return "bg-surface text-fg-muted ring-rule";
  }

  function cellDotClass(value: CellState): string {
    if (value === "ok") return "bg-ok";
    if (value === "partial") return "bg-accent";
    if (value === "ready") return "bg-ok";
    if (value === "missing") return "bg-rule-strong";
    if (value === "blocked") return "bg-bad";
    if (value === "na") return "bg-surface-raised ring-1 ring-rule-strong";
    return "bg-fg-subtle";
  }
</script>

<section class="rounded-md border border-rule bg-surface-raised p-4" data-testid="coverage-gap-matrix">
  <div class="flex flex-wrap items-start justify-between gap-3">
    <div>
      <h3 class="text-base font-semibold text-fg">Coverage Gap Matrix</h3>
      <p class="mt-1 max-w-3xl text-sm text-fg-muted">
        Visual triage across source data, trial tables, extracted findings, model fits,
        reports, and request state.
      </p>
    </div>
    <span class="rounded bg-surface-sunken px-2 py-1 font-mono text-xs text-fg-secondary">
      {filteredRows.length}/{rows.length}
    </span>
  </div>

  <div class="mt-4 flex flex-wrap gap-2 text-xs">
    {#each views as option (option.value)}
      <button
        type="button"
        class={[
          "rounded border px-2.5 py-1 font-semibold",
          view === option.value
            ? "border-accent bg-accent text-white"
            : "border-rule-strong bg-surface-raised text-fg-secondary hover:border-accent hover:text-accent",
        ]}
        onclick={() => (view = option.value)}
      >
        {option.label}
        <span class={view === option.value ? "text-white/80" : "text-fg-muted"}>
          {viewCount(option.value)}
        </span>
      </button>
    {/each}
  </div>

  <div class="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(16rem,0.8fr)_minmax(0,1fr)]">
    <label class="text-xs text-fg-muted">
      <span class="mb-1 block font-semibold text-fg-secondary">Search gaps</span>
      <input
        value={query}
        oninput={(event) => (query = (event.currentTarget as HTMLInputElement).value)}
        type="search"
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        placeholder="paper, protocol, slice, blocker"
        autocomplete="off"
        autocapitalize="none"
        spellcheck="false"
      />
    </label>
    <div class="flex flex-wrap items-end gap-2 text-[11px]">
      {#each ["ok", "partial", "ready", "missing", "blocked", "na"] as state (state)}
        <span class={["inline-flex items-center gap-1 rounded px-1.5 py-1 ring-1", cellClass(state as CellState)]}>
          <span class={["h-2 w-2 rounded-full", cellDotClass(state as CellState)]}></span>
          {cellLabel(state as CellState)}
        </span>
      {/each}
    </div>
  </div>

  {#if filteredRows.length === 0}
    <p class="mt-4 rounded-md border border-rule bg-surface p-4 text-sm text-fg-muted">
      No coverage gaps match the current filters.
    </p>
  {:else}
    <div class="mt-4 hidden overflow-x-auto rounded-md border border-rule md:block">
      <table class="w-full text-sm">
        <thead class="bg-surface text-left text-xs uppercase tracking-wide text-fg-muted">
          <tr>
            <th class="px-3 py-2">Target</th>
            <th class="px-3 py-2">State</th>
            {#each columns as column (column.key)}
              <th class="px-2 py-2 text-center" title={column.title}>{column.label}</th>
            {/each}
            <th class="px-3 py-2">Current blocker</th>
            <th class="px-3 py-2">Next action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-rule">
          {#each filteredRows as row (row.id)}
            <tr>
              <td class="max-w-xs px-3 py-3 align-top">
                <a class="font-semibold text-fg no-underline hover:text-accent" href={row.href}>
                  {row.target_label}
                </a>
                <p class="mt-1 font-mono text-[11px] text-fg-muted">{row.target_id}</p>
                <div class="mt-2 flex flex-wrap gap-1">
                  <span class="rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] uppercase text-fg-muted">
                    {readable(row.target_type)}
                  </span>
                  {#each row.chips.slice(0, 4) as chip (chip)}
                    <span class="rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] text-fg-muted">{chip}</span>
                  {/each}
                </div>
              </td>
              <td class="px-3 py-3 align-top">
                <span class={["inline-flex rounded px-2 py-1 text-[10px] uppercase ring-1", viewClass(row.view)]}>
                  {viewLabel(row.view)}
                </span>
                <span class={["mt-1 block w-fit rounded px-2 py-0.5 text-[10px] uppercase", priorityClass(row.priority)]}>
                  {readable(row.priority)}
                </span>
                <p class="mt-1 text-[11px] text-fg-muted">{readable(row.status)}</p>
                <p class="mt-1 text-[11px] text-fg-muted">{row.source}</p>
              </td>
              {#each columns as column (column.key)}
                <td class="px-2 py-3 text-center align-top">
                  <span
                    class={["inline-flex min-w-14 items-center justify-center gap-1 rounded px-1.5 py-1 text-[10px] ring-1", cellClass(row.cells[column.key])]}
                    title={`${column.title}: ${cellLabel(row.cells[column.key])}`}
                  >
                    <span class={["h-2 w-2 rounded-full", cellDotClass(row.cells[column.key])]}></span>
                    {cellLabel(row.cells[column.key])}
                  </span>
                </td>
              {/each}
              <td class="max-w-xs px-3 py-3 align-top text-xs text-fg-secondary">
                <span class="font-semibold text-fg">{readable(row.blocker)}</span>
                {#if row.detail}
                  <p class="mt-1 line-clamp-3 text-fg-muted">{row.detail}</p>
                {/if}
                {#if row.request_href}
                  <a class="mt-2 inline-flex rounded border border-rule-strong px-2 py-0.5 text-[10px] no-underline hover:border-accent hover:text-accent" href={row.request_href}>
                    {row.request_label ?? "request"}
                  </a>
                {/if}
              </td>
              <td class="max-w-sm px-3 py-3 align-top text-xs text-fg-secondary">
                {row.next_action}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <ul class="mt-4 space-y-3 md:hidden">
      {#each filteredRows as row (row.id)}
        <li class="rounded-md border border-rule bg-surface p-3">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <a class="font-semibold text-fg no-underline hover:text-accent" href={row.href}>
                {row.target_label}
              </a>
              <p class="mt-1 font-mono text-[11px] text-fg-muted">{row.target_id}</p>
            </div>
            <span class={["shrink-0 rounded px-2 py-1 text-[10px] uppercase ring-1", viewClass(row.view)]}>
              {viewLabel(row.view)}
            </span>
          </div>
          <div class="mt-3 grid grid-cols-2 gap-2">
            {#each columns as column (column.key)}
              <div>
                <div class="mb-1 text-[10px] uppercase tracking-wide text-fg-muted">{column.label}</div>
                <span class={["inline-flex w-full items-center justify-center gap-1 rounded px-1.5 py-1 text-[10px] ring-1", cellClass(row.cells[column.key])]}>
                  <span class={["h-2 w-2 rounded-full", cellDotClass(row.cells[column.key])]}></span>
                  {cellLabel(row.cells[column.key])}
                </span>
              </div>
            {/each}
          </div>
          <p class="mt-3 text-xs font-semibold text-fg">{readable(row.blocker)}</p>
          <p class="mt-1 text-xs text-fg-muted">{row.next_action}</p>
        </li>
      {/each}
    </ul>
  {/if}
</section>
