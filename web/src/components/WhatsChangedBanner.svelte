<!--
  WhatsChangedBanner — surfaces "X new findings since your last visit"
  on top of every page when the manifest commit has moved forward
  relative to what the user's browser saw last time. First-time
  visitors see nothing (no baseline to diff against). Dismissing the
  banner snapshots current counts so the next visit's diff is from
  here, not from a months-old snapshot.

  All state lives in a single localStorage key. No server. The
  totals are passed in from the page so we don't need to re-fetch
  the manifest at runtime.
-->
<script lang="ts">
  type Snapshot = {
    commit: string;
    seenAt: number;
    counts: Record<string, number>;
  };

  interface Props {
    commit: string | null;
    counts: Record<string, number>;
    width?: "prose" | "content" | "wide" | "full";
  }

  let { commit, counts, width = "content" }: Props = $props();

  const widthClass: Record<NonNullable<Props["width"]>, string> = {
    prose: "max-w-prose",
    content: "max-w-content",
    wide: "max-w-wide",
    full: "max-w-full",
  };

  const STORAGE_KEY = "behavtaskatlas:lastSeen";

  let snapshot = $state<Snapshot | null>(null);
  let dismissed = $state(false);
  let mounted = $state(false);

  $effect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) snapshot = JSON.parse(raw) as Snapshot;
    } catch (err) {
      console.error("Failed to read what's-changed snapshot", err);
    }
    mounted = true;
  });

  // Compute the diff between the stored snapshot and current counts.
  // Only positive changes show up — a count going down isn't useful as
  // a visitor signal (most likely a curation cleanup). null means
  // either there's no stored snapshot or the commit hasn't moved.
  type Delta = {
    label: string;
    delta: number;
  };

  const deltas = $derived.by<Delta[] | null>(() => {
    if (!mounted || !snapshot || !commit) return null;
    if (snapshot.commit === commit) return null;
    const out: Delta[] = [];
    for (const [key, current] of Object.entries(counts)) {
      const previous = snapshot.counts[key] ?? 0;
      const change = current - previous;
      if (change > 0) {
        out.push({ label: key, delta: change });
      }
    }
    return out;
  });

  const sinceLabel = $derived.by(() => {
    if (!snapshot) return "";
    const ago = Date.now() - snapshot.seenAt;
    const days = Math.floor(ago / (24 * 60 * 60 * 1000));
    if (days <= 0) return "earlier today";
    if (days === 1) return "yesterday";
    if (days < 14) return `${days} days ago`;
    const weeks = Math.floor(days / 7);
    if (weeks < 8) return `${weeks} weeks ago`;
    return new Date(snapshot.seenAt).toLocaleDateString();
  });

  function persistCurrent() {
    if (typeof window === "undefined" || !commit) return;
    const next: Snapshot = {
      commit,
      seenAt: Date.now(),
      counts,
    };
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch (err) {
      console.error("Failed to persist what's-changed snapshot", err);
    }
  }

  function dismiss() {
    persistCurrent();
    dismissed = true;
  }

  // First-ever visit: silently snapshot so subsequent loads can diff.
  $effect(() => {
    if (!mounted || !commit) return;
    if (snapshot === null) persistCurrent();
  });

  const visible = $derived(
    !dismissed && deltas !== null && deltas.length > 0,
  );

  // Format helpers for the banner copy. We translate manifest count
  // keys ("findings", "fits", "papers") into reader-friendly labels.
  const READABLE: Record<string, string> = {
    findings: "findings",
    papers: "papers",
    fits: "model fits",
    slices: "slices",
    protocols: "protocols",
    datasets: "datasets",
    families: "task families",
  };
  function readable(key: string): string {
    return READABLE[key] ?? key.replace(/_/g, " ");
  }
</script>

{#if visible && deltas}
  <div
    role="status"
    aria-live="polite"
    class="border-b border-rule bg-accent-soft text-fg animate-fade-in"
  >
    <div
      class="mx-auto flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 py-2 text-body-xs {widthClass[width]}"
    >
      <span class="font-semibold text-accent">New since {sinceLabel}:</span>
      {#each deltas as delta, i (delta.label)}
        <span class="text-fg-secondary">
          <span class="font-mono text-fg">+{delta.delta}</span>
          {readable(delta.label)}{i < deltas.length - 1 ? "," : ""}
        </span>
      {/each}
      <button
        type="button"
        class="ml-auto text-fg-muted hover:text-accent"
        onclick={dismiss}
      >
        Dismiss
      </button>
    </div>
  </div>
{/if}
