<!--
  MiniRelationshipSlice — a small inline graph that renders the
  paper → protocols → datasets → slices chain for a single finding's
  parent paper.

  Each column shows a count with a labelled list of the records the
  paper touches; the entry that belongs to the active finding is
  highlighted with the encoding-token swatch and an accent ring so
  the reader can see "this finding sits inside a paper that also has
  N protocols / M datasets / K slices" without leaving the rail.

  Inputs are passed in pre-shaped from the page so the component
  works without a graph-index lookup. Hovering a column outline
  pulses the focused element to draw attention; otherwise the markup
  is static.
-->
<script lang="ts">
  type Item = {
    id: string;
    label: string;
    href?: string | null;
    isFocus?: boolean;
  };

  interface Props {
    paper: { id: string; label: string; href?: string | null };
    protocols: Item[];
    datasets: Item[];
    slices: Item[];
    findingId: string;
    findingLabel: string;
  }

  let {
    paper,
    protocols,
    datasets,
    slices,
    findingId,
    findingLabel,
  }: Props = $props();

  type Column = {
    title: string;
    color: string;
    items: Item[];
    fallbackLabel?: string;
  };

  const columns = $derived<Column[]>([
    {
      title: "Paper",
      color: "bg-accent",
      items: [
        {
          id: paper.id,
          label: paper.label,
          href: paper.href ?? null,
          isFocus: true,
        },
      ],
    },
    {
      title: `${protocols.length} protocol${protocols.length === 1 ? "" : "s"}`,
      color: "bg-encoding-node-protocol",
      items: protocols,
      fallbackLabel: "no protocols linked",
    },
    {
      title: `${datasets.length} dataset${datasets.length === 1 ? "" : "s"}`,
      color: "bg-encoding-node-dataset",
      items: datasets,
      fallbackLabel: "no datasets linked",
    },
    {
      title: `${slices.length} slice${slices.length === 1 ? "" : "s"}`,
      color: "bg-encoding-node-slice",
      items: slices,
      fallbackLabel: "no slices bundled",
    },
  ]);

  const focusedColumnIndex = $state<number | null>(null);
  let hoveredColumn = $state<number | null>(null);

  function isHover(index: number): boolean {
    return hoveredColumn === index;
  }
</script>

<div
  class="rounded-md border border-rule bg-surface-raised p-3 text-body-xs"
  aria-label="Relationship slice for this finding's paper"
>
  <p class="mb-2 flex items-baseline justify-between gap-2 text-eyebrow uppercase text-fg-muted">
    <span>This finding's neighbourhood</span>
    <span class="font-mono text-mono-id text-fg-subtle">{findingId}</span>
  </p>
  <div class="grid grid-cols-1 gap-2 sm:grid-cols-[auto_1fr]">
    <p class="text-mono-id text-fg-secondary sm:hidden">
      {findingLabel}
    </p>
    <div class="grid grid-cols-4 gap-2">
      {#each columns as column, columnIndex (column.title)}
        <div
          class={[
            "rounded border px-2 py-1.5 transition-colors",
            isHover(columnIndex)
              ? "border-rule-emphasis bg-surface"
              : "border-rule",
          ]}
          onmouseenter={() => (hoveredColumn = columnIndex)}
          onmouseleave={() => (hoveredColumn = null)}
          role="presentation"
        >
          <div class="flex items-center gap-1.5">
            <span
              class={["h-2 w-2 shrink-0 rounded-full", column.color]}
              aria-hidden="true"
            ></span>
            <span class="text-eyebrow uppercase text-fg-muted">{column.title}</span>
          </div>
          <ul class="mt-1.5 space-y-0.5">
            {#if column.items.length === 0}
              <li class="text-mono-id text-fg-subtle">
                {column.fallbackLabel ?? "—"}
              </li>
            {:else}
              {#each column.items as item (item.id)}
                <li>
                  {#if item.href}
                    <a
                      href={item.href}
                      class={[
                        "block truncate rounded px-1 py-0.5 text-mono-id no-underline",
                        item.isFocus
                          ? "bg-accent-soft font-semibold text-accent ring-1 ring-accent"
                          : "text-fg-secondary hover:text-accent",
                      ]}
                      title={item.label}
                    >
                      {item.label}
                    </a>
                  {:else}
                    <span
                      class={[
                        "block truncate rounded px-1 py-0.5 text-mono-id",
                        item.isFocus
                          ? "bg-accent-soft font-semibold text-accent ring-1 ring-accent"
                          : "text-fg-secondary",
                      ]}
                      title={item.label}
                    >
                      {item.label}
                    </span>
                  {/if}
                </li>
              {/each}
            {/if}
          </ul>
        </div>
      {/each}
    </div>
  </div>
  <p class="mt-2 text-mono-id text-fg-muted">
    Highlighted rows belong to this finding. Hover a column for
    contrast.
  </p>
</div>
