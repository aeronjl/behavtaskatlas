<!--
  ConfidenceChip — 4-segment visual marker for AIC selection confidence.

  The atlas uses the standard ΔAIC ladder:
  - decisive          ΔAIC ≥ 10  → 4 / 4 filled segments
  - supported         ΔAIC ≥ 2   → 3 / 4 filled segments
  - close             ΔAIC < 2   → 2 / 4 filled segments
  - single_candidate  no rival   → 1 / 4 filled segments

  Each level has its own colour token (declared in styles/global.css)
  so a chip dropped into a 100-row table reads at a glance: green for
  decisive, teal for supported, amber for close, slate for single.

  Pass the level + the delta you want to render. Optional `showLabel`
  swaps in / out the textual tag, and `size` picks chip dimensions.
-->
<script lang="ts">
  type Confidence =
    | "decisive"
    | "supported"
    | "close"
    | "single_candidate"
    | (string & {});

  interface Props {
    confidence?: Confidence | null;
    /** Δ AIC to the next-best variant; rendered after the label when present. */
    delta?: number | null;
    /** Toggle the textual label (default: shown). */
    showLabel?: boolean;
    /** Compact for inside dense tables, default for stand-alone use. */
    size?: "sm" | "md";
    class?: string;
  }

  let {
    confidence,
    delta = null,
    showLabel = true,
    size = "sm",
    class: className = "",
  }: Props = $props();

  const FILLED: Record<string, number> = {
    decisive: 4,
    supported: 3,
    close: 2,
    single_candidate: 1,
  };

  const READABLE: Record<string, string> = {
    decisive: "decisive",
    supported: "supported",
    close: "close",
    single_candidate: "single",
  };

  const FILL_CLASS: Record<string, string> = {
    decisive: "bg-confidence-decisive",
    supported: "bg-confidence-supported",
    close: "bg-confidence-close",
    single_candidate: "bg-confidence-single",
  };

  const filled = $derived(
    confidence && FILLED[confidence] !== undefined ? FILLED[confidence] : 0,
  );
  const label = $derived(
    confidence && READABLE[confidence]
      ? READABLE[confidence]
      : confidence
        ? confidence.replace(/_/g, " ")
        : "—",
  );
  const fillBg = $derived(
    confidence && FILL_CLASS[confidence]
      ? FILL_CLASS[confidence]
      : "bg-fg-muted",
  );
  const segH = $derived(size === "md" ? "h-2.5" : "h-2");
  const segW = $derived(size === "md" ? "w-2" : "w-1.5");

  function fmtDelta(value: number | null): string {
    if (value === null || !Number.isFinite(value)) return "";
    if (value === 0) return "Δ —";
    return `Δ ${value.toFixed(1)}`;
  }
</script>

<span
  class={["inline-flex items-center gap-1.5", className]}
  aria-label={confidence
    ? `Confidence: ${label}${delta !== null && Number.isFinite(delta) ? ` (delta ${delta.toFixed(1)})` : ""}`
    : "Confidence not available"}
>
  <span class="inline-flex shrink-0 gap-0.5" aria-hidden="true">
    {#each [0, 1, 2, 3] as i (i)}
      <span class={["rounded-sm", segH, segW, i < filled ? fillBg : "bg-rule"]}
      ></span>
    {/each}
  </span>
  {#if showLabel}
    <span class="text-mono-id text-fg-secondary">
      {label}{delta !== null && Number.isFinite(delta) ? ` · ${fmtDelta(delta)}` : ""}
    </span>
  {/if}
</span>
