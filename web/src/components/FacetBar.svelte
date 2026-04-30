<!--
  FacetBar — shared filter shell for the browser components.

  Handles:
  - Search input
  - Sort dropdown
  - Optional secondary dropdown (e.g. report/source state)
  - Optional preset pill row + clear-all button
  - Multi-select pill-cloud facets

  Does NOT handle URL sync — that stays in each consumer because the
  param shapes differ (some prefix with `model_*`, some don't, defaults
  vary). Consumers two-way bind `query`, `sortMode`, `stateMode`, and
  `selected`, then run their own filter/sort logic on the result.
-->
<script lang="ts">
  type FacetOption = { value: string; label: string; count: number };
  type Facet = {
    key: string;
    label: string;
    options: FacetOption[];
    /** "multi" (default) renders pill clusters; "single" renders a
     * `<select>` dropdown with an "All X" entry. State shape is the
     * same — `selected[key]` holds 0 or 1 element for single-select. */
    mode?: "multi" | "single";
    /** Override for the "All X" option label in single-select mode. */
    allLabel?: string;
  };
  type Preset = { key: string; label: string; description?: string };
  type SimpleOption = { value: string; label: string };

  let {
    // Search
    searchPlaceholder = "Search…",
    query = $bindable(""),

    // Sort
    sortOptions = [] as SimpleOption[],
    sortMode = $bindable(""),
    sortLabel = "Sort",

    // Optional second dropdown
    stateOptions = [] as SimpleOption[],
    stateMode = $bindable(""),
    stateLabel = "State",

    // Presets
    presets = [] as Preset[],
    isPresetActive,
    onPreset,

    // Multi-select facets
    facets = [] as Facet[],
    selected = $bindable({} as Record<string, Set<string>>),

    // Reset
    activeFilterCount = 0,
    onClearAll,
  }: {
    searchPlaceholder?: string;
    query?: string;
    sortOptions: SimpleOption[];
    sortMode?: string;
    sortLabel?: string;
    stateOptions?: SimpleOption[];
    stateMode?: string;
    stateLabel?: string;
    presets?: Preset[];
    isPresetActive?: (key: string) => boolean;
    onPreset?: (key: string) => void;
    facets?: Facet[];
    selected?: Record<string, Set<string>>;
    activeFilterCount?: number;
    onClearAll?: () => void;
  } = $props();

  function toggleFacet(key: string, value: string) {
    const next = new Set(selected[key] ?? new Set<string>());
    if (next.has(value)) next.delete(value);
    else next.add(value);
    selected = { ...selected, [key]: next };
  }

  function setSingle(key: string, value: string) {
    selected = {
      ...selected,
      [key]: value === "" ? new Set<string>() : new Set([value]),
    };
  }

  function singleValue(key: string): string {
    const set = selected[key];
    if (!set || set.size === 0) return "";
    return Array.from(set)[0] ?? "";
  }

  function clearFacet(key: string) {
    selected = { ...selected, [key]: new Set<string>() };
  }

  // Responsive grid for the facet row depends on facet count so a 2-facet
  // page doesn't get a 5-column shrink.
  const facetGridClass = $derived(
    facets.length >= 5
      ? "lg:grid-cols-3 xl:grid-cols-5"
      : facets.length === 4
        ? "md:grid-cols-2 lg:grid-cols-4"
        : facets.length === 3
          ? "md:grid-cols-3"
          : facets.length === 2
            ? "sm:grid-cols-2"
            : "",
  );

  // Top-row grid depends on whether the optional state dropdown is shown.
  const topRowGridClass = $derived(
    stateOptions.length > 0
      ? "lg:grid-cols-[minmax(0,1.8fr)_minmax(11rem,0.75fr)_minmax(11rem,0.75fr)]"
      : "lg:grid-cols-[minmax(0,1.8fr)_minmax(11rem,0.75fr)]",
  );
</script>

<section class="rounded-md border border-rule bg-surface-raised p-4">
  <div class={["grid grid-cols-1 gap-3", topRowGridClass]}>
    <label class="text-body-xs text-fg-secondary">
      <span class="mb-1 block font-semibold text-fg-secondary">Search</span>
      <input
        type="search"
        bind:value={query}
        placeholder={searchPlaceholder}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-3 py-2 text-body shadow-sm focus:border-rule-emphasis focus:outline-none focus:ring-1 focus:ring-accent"
        autocomplete="off"
        autocapitalize="none"
        spellcheck="false"
      />
    </label>

    {#if stateOptions.length > 0}
      <label class="text-body-xs text-fg-secondary">
        <span class="mb-1 block font-semibold text-fg-secondary">{stateLabel}</span>
        <select
          bind:value={stateMode}
          class="w-full rounded-md border border-rule-strong bg-surface-raised px-3 py-2 text-body shadow-sm"
        >
          {#each stateOptions as option (option.value)}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>
    {/if}

    <label class="text-body-xs text-fg-secondary">
      <span class="mb-1 block font-semibold text-fg-secondary">{sortLabel}</span>
      <select
        bind:value={sortMode}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-3 py-2 text-body shadow-sm"
      >
        {#each sortOptions as option (option.value)}
          <option value={option.value}>{option.label}</option>
        {/each}
      </select>
    </label>
  </div>

  {#if presets.length > 0 || activeFilterCount > 0}
    <div class="mt-3 flex flex-wrap gap-2 text-body-xs">
      {#each presets as preset (preset.key)}
        {@const isOn = isPresetActive ? isPresetActive(preset.key) : false}
        <button
          type="button"
          aria-pressed={isOn}
          title={preset.description}
          class={[
            "rounded border px-2 py-1",
            isOn
              ? "border-accent bg-accent text-fg-inverse"
              : "border-rule-strong bg-surface-raised text-fg-secondary hover:border-rule-emphasis hover:text-accent",
          ]}
          onclick={() => onPreset?.(preset.key)}
        >
          {preset.label}
        </button>
      {/each}
      {#if activeFilterCount > 0}
        <button
          type="button"
          class="rounded border border-rule-strong bg-surface px-2 py-1 font-semibold text-fg hover:border-rule-emphasis hover:text-accent"
          onclick={() => onClearAll?.()}
        >
          clear {activeFilterCount}
        </button>
      {/if}
    </div>
  {/if}

  {#if facets.length > 0}
    <div class={["mt-4 grid grid-cols-1 gap-3", facetGridClass]}>
      {#each facets as facet (facet.key)}
        {@const mode = facet.mode ?? "multi"}
        <div class="min-w-0">
          <div class="mb-1 flex items-center justify-between gap-2 text-body-xs">
            <h3 class="font-semibold text-fg-secondary">{facet.label}</h3>
            {#if mode === "multi" && (selected[facet.key] ?? new Set()).size > 0}
              <button
                type="button"
                class="text-fg-muted hover:text-accent"
                onclick={() => clearFacet(facet.key)}
              >
                all
              </button>
            {/if}
          </div>
          {#if mode === "single"}
            <select
              value={singleValue(facet.key)}
              onchange={(event) =>
                setSingle(facet.key, (event.currentTarget as HTMLSelectElement).value)}
              class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-body-xs"
            >
              <option value="">{facet.allLabel ?? `All ${facet.label.toLowerCase()}`}</option>
              {#each facet.options as option (option.value)}
                <option value={option.value}>{option.label} · {option.count}</option>
              {/each}
            </select>
          {:else}
            <div class="flex max-h-36 flex-wrap gap-1 overflow-y-auto pr-1">
              {#each facet.options as option (option.value)}
                {@const sel = (selected[facet.key] ?? new Set()).has(option.value)}
                <button
                  type="button"
                  aria-pressed={sel}
                  class={[
                    "max-w-full rounded border px-2 py-0.5 text-left text-mono-id",
                    sel
                      ? "border-accent bg-accent text-fg-inverse"
                      : "border-rule-strong bg-surface-raised text-fg-secondary hover:border-rule-emphasis hover:text-accent",
                  ]}
                  onclick={() => toggleFacet(facet.key, option.value)}
                >
                  <span class="inline-block max-w-[15rem] truncate align-bottom">{option.label}</span>
                  <span class={["ml-1 font-mono", sel ? "text-fg-inverse" : "text-fg-muted"]}>
                    {option.count}
                  </span>
                </button>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</section>
