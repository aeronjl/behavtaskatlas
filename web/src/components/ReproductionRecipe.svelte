<!--
  ReproductionRecipe — copy-paste shell snippet that reproduces a slice's
  artifacts locally at the exact build commit. Replaces the old
  "run … locally" prose with a literal recipe a collaborator can copy
  into their terminal.

  The slice's `extra` group is derived from the id so a slice with
  scipy-only deps shows `--extra clicks`, IBL slices show `--extra ibl`,
  etc. When the per-slice extras don't fit the heuristic, the recipe
  falls back to plain `uv sync` and notes the README for the right
  extras group.
-->
<script lang="ts">
  interface Props {
    sliceId: string;
    /** The atlas commit at build time; the recipe pins the checkout. */
    commit?: string | null;
    /** Optional override; only relevant when the heuristic mis-derives. */
    extra?: string | null;
  }

  let { sliceId, commit = null, extra = null }: Props = $props();

  // Heuristic: the slice id encodes its dataset family closely enough
  // that we can assign an `--extra` group. This is intentionally simple
  // — the README is the canonical source if the heuristic ever falls
  // out of sync with reality.
  function deriveExtra(id: string): string | null {
    const base = id.replace(/^slice\./, "");
    if (base.startsWith("ibl") || base.startsWith("mouse-")) return "ibl";
    if (base.includes("clicks")) return "clicks";
    if (base.includes("random-dot-motion") || base.includes("rdm")) return "rdm";
    if (base.includes("visual-contrast") || base.includes("walsh"))
      return "visual";
    return null;
  }

  const resolvedExtra = $derived(extra ?? deriveExtra(sliceId));
  const baseId = $derived(sliceId.replace(/^slice\./, ""));
  const recipe = $derived(
    [
      "git clone https://github.com/aeronjl/behavtaskatlas.git",
      "cd behavtaskatlas",
      commit ? `git checkout ${commit}` : null,
      resolvedExtra ? `uv sync --extra ${resolvedExtra}` : "uv sync",
      `uv run behavtaskatlas ${baseId}-download`,
      `uv run behavtaskatlas ${baseId}-harmonize`,
      `uv run behavtaskatlas ${baseId}-analyze`,
      `uv run behavtaskatlas ${baseId}-report`,
    ]
      .filter((line): line is string => line !== null)
      .join("\n"),
  );

  let copyState = $state<"idle" | "copied" | "error">("idle");

  async function copyRecipe() {
    if (typeof window === "undefined") return;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(recipe);
      } else {
        const ta = document.createElement("textarea");
        ta.value = recipe;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      copyState = "copied";
      setTimeout(() => (copyState = "idle"), 1500);
    } catch (err) {
      console.error(err);
      copyState = "error";
      setTimeout(() => (copyState = "idle"), 1500);
    }
  }
</script>

<section class="rounded-md border border-rule bg-surface-raised">
  <header class="flex flex-wrap items-baseline justify-between gap-3 border-b border-rule px-4 py-3">
    <div>
      <p class="text-eyebrow uppercase text-fg-muted">Reproduce locally</p>
      <h3 class="mt-1 text-body font-semibold text-fg">
        Run the slice pipeline at this commit
      </h3>
    </div>
    <button
      type="button"
      class="rounded-md border border-rule-strong bg-surface-raised px-2.5 py-1 text-body-xs text-fg-secondary hover:border-rule-emphasis hover:text-accent"
      onclick={copyRecipe}
    >
      {copyState === "copied"
        ? "Copied ✓"
        : copyState === "error"
          ? "Copy failed"
          : "Copy recipe"}
    </button>
  </header>
  <pre
    class="overflow-x-auto px-4 py-3 font-mono text-mono-num leading-6 text-fg-secondary"
  >{recipe}</pre>
  <p class="border-t border-rule px-4 py-2 text-mono-id text-fg-muted">
    {#if resolvedExtra}
      Extras group <code class="rounded bg-surface-sunken px-1">{resolvedExtra}</code>
      pulls in the analysis dependencies for this family.
    {:else}
      No <code class="rounded bg-surface-sunken px-1">--extra</code>
      group inferred — see the repository README for the right extras
      flag if the slice has analysis-only deps.
    {/if}
    {#if commit}
      Recipe pinned to commit
      <code class="rounded bg-surface-sunken px-1">{commit}</code>
      so a teammate runs the same code path the deploy used.
    {/if}
  </p>
</section>
