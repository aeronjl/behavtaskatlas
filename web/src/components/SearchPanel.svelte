<script lang="ts">
  import type { SearchPayload, SearchEntry } from "../lib/search";
  import { searchIndex } from "../lib/search";

  let initialQuery = "";
  let initialTypes = "";
  if (typeof window !== "undefined") {
    const params = new URLSearchParams(window.location.search);
    initialQuery = params.get("q") ?? "";
    initialTypes = params.get("type") ?? "";
  }

  const TYPE_LABEL: Record<string, string> = {
    paper: "Paper",
    task_family: "Task family",
    protocol: "Protocol",
    dataset: "Dataset",
    vertical_slice: "Slice",
    finding: "Finding",
    comparison: "Comparison",
    model: "Model",
    story: "Story",
    data_request: "Data request",
  };
  const ALL_TYPES = Object.keys(TYPE_LABEL);

  const payload: SearchPayload = searchIndex;

  function initialTypeSet(): Set<string> {
    if (!initialTypes) return new Set(ALL_TYPES);
    const selected = initialTypes
      .split(",")
      .map((value) => value.trim())
      .filter((value) => ALL_TYPES.includes(value));
    return selected.length > 0 ? new Set(selected) : new Set(ALL_TYPES);
  }

  let query = $state(initialQuery.trim());
  let activeTypes = $state(initialTypeSet());
  let inputEl: HTMLInputElement | null = $state(null);

  const activeFilterCount = $derived(
    (query.trim().length > 0 ? 1 : 0) +
      (activeTypes.size === ALL_TYPES.length ? 0 : 1),
  );

  function syncUrl() {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    const trimmed = query.trim();
    if (trimmed.length > 0) params.set("q", trimmed);
    if (activeTypes.size !== ALL_TYPES.length) {
      params.set("type", ALL_TYPES.filter((type) => activeTypes.has(type)).join(","));
    }
    const search = params.toString();
    const next = `${window.location.pathname}${search ? `?${search}` : ""}${window.location.hash}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(null, "", next);
    }
  }

  function toggleType(t: string) {
    const next = new Set(activeTypes);
    if (next.has(t)) next.delete(t); else next.add(t);
    if (next.size === 0) ALL_TYPES.forEach((x) => next.add(x));
    activeTypes = next;
    syncUrl();
  }

  function clearAll() {
    query = "";
    activeTypes = new Set(ALL_TYPES);
    syncUrl();
  }

  function updateQuery(event: Event) {
    query = (event.currentTarget as HTMLInputElement).value;
    syncUrl();
  }

  function score(entry: SearchEntry, tokens: string[]): number {
    if (tokens.length === 0) return 0;
    const title = entry.title.toLowerCase();
    const subtitle = entry.subtitle.toLowerCase();
    const body = entry.body.toLowerCase();
    const keywords = entry.keywords.join(" ").toLowerCase();
    let total = 0;
    for (const token of tokens) {
      let matched = false;
      if (title.includes(token)) {
        total += title.startsWith(token) ? 14 : 10;
        matched = true;
      }
      if (subtitle.includes(token)) {
        total += 5;
        matched = true;
      }
      if (keywords.includes(token)) {
        total += 3;
        matched = true;
      }
      if (body.includes(token)) {
        total += 1;
        matched = true;
      }
      if (!matched) return 0;
    }
    return total;
  }

  function highlight(text: string, tokens: string[]): string {
    if (!text || tokens.length === 0) return text;
    const escaped = tokens
      .filter((t) => t.length > 0)
      .map((t) => t.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&"));
    if (escaped.length === 0) return text;
    const re = new RegExp(`(${escaped.join("|")})`, "gi");
    return text.replace(re, "<mark class=\"bg-amber-100\">$1</mark>");
  }

  const tokens = $derived(
    query
      .toLowerCase()
      .split(/\s+/)
      .map((t) => t.trim())
      .filter((t) => t.length > 0),
  );

  const rankedResults = $derived(
    payload.entries
      .filter((e) => activeTypes.has(e.type))
      .map((e) => ({ entry: e, s: tokens.length === 0 ? 0 : score(e, tokens) }))
      .filter((r) => tokens.length === 0 || r.s > 0)
      .sort((a, b) => b.s - a.s || a.entry.title.localeCompare(b.entry.title)),
  );

  const results = $derived(
    rankedResults.slice(0, 100),
  );

  $effect(() => {
    if (inputEl && initialQuery) inputEl.focus();
  });

</script>

<div class="space-y-3">
  <input
    bind:this={inputEl}
    value={query}
    oninput={updateQuery}
    type="search"
    placeholder="Search papers, models, stories, requests, findings…"
    class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
    autocomplete="off"
    autocapitalize="none"
    spellcheck="false"
  />

  <div class="flex flex-wrap items-center gap-2 text-xs text-slate-600">
    <span class="text-slate-500">Filter:</span>
    {#each ALL_TYPES as t (t)}
      {@const active = activeTypes.has(t)}
      <button
        type="button"
        class:bg-accent={active}
        class:text-white={active}
        class:border-accent={active}
        class:bg-white={!active}
        class:text-slate-700={!active}
        class:border-slate-300={!active}
        class="rounded border px-2 py-0.5"
        onclick={() => toggleType(t)}
      >
        {TYPE_LABEL[t]} · {payload.counts[t] ?? 0}
      </button>
    {/each}
    {#if activeFilterCount > 0}
      <button
        type="button"
        class="rounded border border-slate-300 bg-slate-50 px-2 py-0.5 font-semibold text-slate-800 hover:border-accent hover:text-accent"
        onclick={clearAll}
      >
        clear {activeFilterCount}
      </button>
    {/if}
  </div>

  <p class="text-xs text-slate-500">
    {tokens.length === 0
      ? `Showing ${results.length} of ${rankedResults.length} indexed records.`
      : `Showing ${results.length} of ${rankedResults.length} match${rankedResults.length === 1 ? "" : "es"} for "${query}".`}
  </p>

  {#if results.length === 0 && tokens.length > 0}
    <section class="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600">
      <p>No matches. Try a broader query or toggle more record types.</p>
      {#if activeFilterCount > 0}
        <button type="button" class="mt-3 rounded border border-slate-300 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-800 hover:border-accent hover:text-accent" onclick={clearAll}>
          Clear filters
        </button>
      {/if}
    </section>
  {:else}
    <ul class="divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
      {#each results as { entry } (entry.id)}
        <li class="px-3 py-2 text-sm">
          <div class="flex items-baseline justify-between gap-3">
            <a
              class="text-slate-900 no-underline hover:text-accent"
              href={entry.href}
            >
              <span>{@html highlight(entry.title, tokens)}</span>
            </a>
            <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-500">
              {TYPE_LABEL[entry.type] ?? entry.type}
            </span>
          </div>
          {#if entry.subtitle}
            <p class="mt-0.5 text-xs text-slate-600">
              {@html highlight(entry.subtitle, tokens)}
            </p>
          {/if}
          {#if entry.body}
            <p class="mt-0.5 line-clamp-2 text-xs text-slate-500">
              {@html highlight(entry.body, tokens)}
            </p>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>
