<script lang="ts">
  import type { SearchEntry, SearchPayload } from "../lib/search";
  import { searchIndex } from "../lib/search";

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

  const payload: SearchPayload = searchIndex;

  let isOpen = $state(false);
  let query = $state("");
  let activeIndex = $state(0);
  let inputEl: HTMLInputElement | null = $state(null);
  let listEl: HTMLUListElement | null = $state(null);

  function open() {
    isOpen = true;
    query = "";
    activeIndex = 0;
    queueMicrotask(() => inputEl?.focus());
  }

  function close() {
    isOpen = false;
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
    // Bias paper/comparison/story/model over deep-leaf records when scores tie.
    if (
      entry.type === "paper" ||
      entry.type === "comparison" ||
      entry.type === "story" ||
      entry.type === "model"
    ) {
      total *= 1.1;
    }
    return total;
  }

  const tokens = $derived(
    query
      .toLowerCase()
      .split(/\s+/)
      .map((t) => t.trim())
      .filter((t) => t.length > 0),
  );

  const results = $derived.by<SearchEntry[]>(() => {
    if (tokens.length === 0) return [];
    return payload.entries
      .map((entry) => ({ entry, s: score(entry, tokens) }))
      .filter((r) => r.s > 0)
      .sort((a, b) => b.s - a.s || a.entry.title.localeCompare(b.entry.title))
      .slice(0, 12)
      .map((r) => r.entry);
  });

  $effect(() => {
    // Reset selection cursor whenever the query changes.
    if (results.length === 0) activeIndex = 0;
    else if (activeIndex >= results.length) activeIndex = results.length - 1;
  });

  function handleKeydown(event: KeyboardEvent) {
    const isPaletteShortcut =
      (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";

    if (isPaletteShortcut) {
      event.preventDefault();
      if (isOpen) close();
      else open();
      return;
    }

    if (!isOpen) return;
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (results.length > 0) activeIndex = (activeIndex + 1) % results.length;
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      if (results.length > 0)
        activeIndex = (activeIndex - 1 + results.length) % results.length;
      return;
    }
    if (event.key === "Enter") {
      const target = results[activeIndex];
      if (target) {
        event.preventDefault();
        window.location.href = target.href;
      }
    }
  }

  $effect(() => {
    if (typeof window === "undefined") return;
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  });

  $effect(() => {
    if (!isOpen) return;
    if (typeof document === "undefined") return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  });

  $effect(() => {
    if (!listEl) return;
    const active = listEl.querySelector('[data-active="true"]') as HTMLElement | null;
    active?.scrollIntoView({ block: "nearest" });
  });
</script>

{#if isOpen}
  <div
    class="fixed inset-0 z-50 flex items-start justify-center bg-fg/30 px-4 pt-20"
    onclick={close}
    onkeydown={(event) => {
      if (event.key === "Escape") close();
    }}
    role="dialog"
    aria-modal="true"
    aria-label="Search the atlas"
    tabindex="-1"
  >
    <div
      class="w-full max-w-xl overflow-hidden rounded-md border border-rule bg-surface-raised shadow-2xl"
      role="presentation"
      onclick={(event) => event.stopPropagation()}
      onkeydown={(event) => event.stopPropagation()}
    >
      <div class="flex items-center gap-2 border-b border-rule px-4 py-3">
        <span class="text-fg-subtle" aria-hidden="true">🔍</span>
        <input
          bind:this={inputEl}
          bind:value={query}
          type="search"
          placeholder="Search papers, findings, models, stories…"
          class="w-full bg-transparent text-sm text-fg outline-none placeholder:text-fg-subtle"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
        />
        <kbd class="rounded bg-surface-sunken px-1.5 py-0.5 font-mono text-[10px] text-fg-muted">
          Esc
        </kbd>
      </div>

      {#if tokens.length === 0}
        <div class="px-4 py-6 text-sm text-fg-muted">
          <p>{payload.counts.total} indexed records.</p>
          <p class="mt-2 text-xs">
            Type to search across papers, task families, protocols, datasets,
            slices, findings, models, stories, data requests, and comparisons. <kbd
              class="rounded bg-surface-sunken px-1 font-mono text-[10px]"
              >↑</kbd
            >
            <kbd class="rounded bg-surface-sunken px-1 font-mono text-[10px]">↓</kbd>
            navigate, <kbd class="rounded bg-surface-sunken px-1 font-mono text-[10px]"
              >↵</kbd
            >
            opens.
          </p>
        </div>
      {:else if results.length === 0}
        <p class="px-4 py-6 text-sm text-fg-muted">
          No matches for "{query}".
        </p>
      {:else}
        <ul
          bind:this={listEl}
          class="max-h-[60vh] divide-y divide-rule overflow-y-auto"
        >
          {#each results as entry, index (entry.id)}
            {@const isActive = index === activeIndex}
            <li>
              <a
                href={entry.href}
                data-active={isActive ? "true" : "false"}
                class={[
                  "flex flex-col gap-0.5 px-4 py-2.5 no-underline",
                  isActive ? "bg-accent-soft" : "hover:bg-surface",
                ]}
                onmouseenter={() => (activeIndex = index)}
              >
                <div class="flex items-baseline justify-between gap-3">
                  <span class="text-sm text-fg">{entry.title}</span>
                  <span
                    class="rounded bg-surface-sunken px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-fg-muted"
                  >
                    {TYPE_LABEL[entry.type] ?? entry.type}
                  </span>
                </div>
                {#if entry.subtitle}
                  <p class="text-xs text-fg-muted">{entry.subtitle}</p>
                {/if}
              </a>
            </li>
          {/each}
        </ul>
      {/if}

      <footer
        class="flex items-center justify-between border-t border-rule bg-surface px-4 py-2 text-[11px] text-fg-muted"
      >
        <span>
          <kbd class="rounded bg-surface-raised px-1 font-mono">⌘</kbd>+<kbd
            class="rounded bg-surface-raised px-1 font-mono">K</kbd
          > to toggle
        </span>
        <a class="text-accent" href="/search?q={encodeURIComponent(query)}"
          >Open search page →</a
        >
      </footer>
    </div>
  </div>
{/if}
