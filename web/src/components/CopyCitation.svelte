<script lang="ts">
  let {
    text,
    url,
  }: {
    text: string;
    url: string;
  } = $props();

  let copied = $state(false);

  async function copyCitation() {
    await navigator.clipboard.writeText(text);
    copied = true;
    window.setTimeout(() => {
      copied = false;
    }, 1600);
  }
</script>

<div class="rounded-md border border-rule bg-surface-raised p-4">
  <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
    <h2 class="text-sm font-semibold text-fg-secondary">Cite this finding</h2>
    <button
      type="button"
      class="rounded-md border border-rule-strong bg-surface-raised px-2 py-1 text-xs text-fg-secondary hover:bg-surface"
      onclick={copyCitation}
    >
      {copied ? "Copied" : "Copy citation"}
    </button>
  </div>
  <p class="mb-2 break-all font-mono text-xs text-fg-muted">{url}</p>
  <textarea
    readonly
    rows="4"
    class="w-full resize-y rounded-md border border-rule-strong bg-surface px-2 py-1.5 font-mono text-xs text-fg-secondary"
    value={text}
  ></textarea>
</div>
