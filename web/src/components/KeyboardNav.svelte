<!--
  KeyboardNav — site-wide keyboard shortcuts.

  Two-key chord: press `g` then a destination letter to navigate.
  Single keys: `?` toggles the help overlay; `Escape` closes it.

  Inputs are excluded by checking the active element's tag, contentEditable,
  and ARIA role so typing in a search box never triggers navigation. The
  ⌘K palette continues to live in SearchPalette and is not handled here.
-->
<script lang="ts">
  type Shortcut = {
    keys: string;
    label: string;
    href: string;
  };

  const shortcuts: Shortcut[] = [
    { keys: "g h", label: "Home", href: "/" },
    { keys: "g f", label: "Findings", href: "/findings" },
    { keys: "g p", label: "Papers", href: "/papers" },
    { keys: "g m", label: "Models", href: "/models" },
    { keys: "g s", label: "Slices", href: "/slices" },
    { keys: "g c", label: "Compare", href: "/compare" },
    { keys: "g t", label: "Stories", href: "/stories" },
    { keys: "g o", label: "Catalog", href: "/catalog" },
    { keys: "g n", label: "Network", href: "/graph" },
    { keys: "g a", label: "Atlas health", href: "/atlas-health" },
  ];
  const destByLetter = new Map<string, string>(
    shortcuts.map((s) => [s.keys.split(" ")[1], s.href]),
  );

  let helpOpen = $state(false);
  let pendingChord = $state(false);
  let chordTimer: number | null = null;

  function clearChord() {
    pendingChord = false;
    if (chordTimer !== null) {
      window.clearTimeout(chordTimer);
      chordTimer = null;
    }
  }

  function isTypingTarget(target: EventTarget | null): boolean {
    if (!(target instanceof HTMLElement)) return false;
    const tag = target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    if (target.isContentEditable) return true;
    const role = target.getAttribute("role");
    if (role === "textbox" || role === "combobox") return true;
    return false;
  }

  function handleKey(event: KeyboardEvent) {
    // Always reset chord on a modifier — Cmd/Ctrl-prefixed keys are not
    // ours (they're for the palette, browser nav, etc.).
    if (event.metaKey || event.ctrlKey || event.altKey) {
      clearChord();
      return;
    }
    if (isTypingTarget(event.target)) {
      clearChord();
      return;
    }

    if (event.key === "Escape") {
      if (helpOpen) {
        helpOpen = false;
        event.preventDefault();
      }
      clearChord();
      return;
    }

    if (event.key === "?") {
      helpOpen = !helpOpen;
      event.preventDefault();
      clearChord();
      return;
    }

    if (pendingChord) {
      const dest = destByLetter.get(event.key.toLowerCase());
      clearChord();
      if (dest) {
        event.preventDefault();
        helpOpen = false;
        window.location.href = dest;
      }
      return;
    }

    if (event.key === "g" && !event.shiftKey) {
      pendingChord = true;
      // 1-second window for the second key — long enough to be forgiving,
      // short enough that a stray `g` doesn't capture a later keypress.
      chordTimer = window.setTimeout(() => {
        pendingChord = false;
        chordTimer = null;
      }, 1000);
    }
  }

  $effect(() => {
    if (typeof window === "undefined") return;
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  });

  $effect(() => {
    if (!helpOpen || typeof document === "undefined") return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  });

  function closeHelp() {
    helpOpen = false;
  }
</script>

{#if pendingChord}
  <div
    class="pointer-events-none fixed bottom-6 left-1/2 z-40 -translate-x-1/2 rounded-md bg-fg/90 px-3 py-1.5 text-body-xs font-mono text-fg-inverse shadow-lg"
    aria-live="polite"
  >
    <span class="opacity-80">g</span><span class="ml-2 opacity-60">+ destination key (h/f/p/m/s/c/t/o/n/a)</span>
  </div>
{/if}

{#if helpOpen}
  <div
    class="fixed inset-0 z-50 flex items-start justify-center bg-fg/30 px-4 pt-20"
    onclick={closeHelp}
    onkeydown={(event) => {
      if (event.key === "Escape") closeHelp();
    }}
    role="dialog"
    aria-modal="true"
    aria-label="Keyboard shortcuts"
    tabindex="-1"
  >
    <div
      class="w-full max-w-lg overflow-hidden rounded-md border border-rule bg-surface-raised shadow-2xl"
      role="presentation"
      onclick={(event) => event.stopPropagation()}
      onkeydown={(event) => event.stopPropagation()}
    >
      <header class="flex items-baseline justify-between gap-3 border-b border-rule px-4 py-3">
        <div>
          <p class="text-eyebrow uppercase text-fg-muted">Keyboard shortcuts</p>
          <h2 class="mt-0.5 text-h3 text-fg">Move around without leaving the keyboard</h2>
        </div>
        <kbd class="rounded bg-surface-sunken px-2 py-1 font-mono text-mono-id text-fg-secondary">
          Esc
        </kbd>
      </header>
      <div class="grid grid-cols-1 gap-x-6 gap-y-2 px-4 py-4 sm:grid-cols-2">
        {#each shortcuts as shortcut (shortcut.keys)}
          <div class="flex items-baseline justify-between gap-3 text-body-xs">
            <span class="text-fg-secondary">{shortcut.label}</span>
            <span class="font-mono text-fg-muted">
              {#each shortcut.keys.split(" ") as key, i (i)}
                {#if i > 0}<span class="mx-1 opacity-50">then</span>{/if}
                <kbd class="rounded bg-surface-sunken px-1.5 py-0.5">{key}</kbd>
              {/each}
            </span>
          </div>
        {/each}
        <div class="flex items-baseline justify-between gap-3 text-body-xs">
          <span class="text-fg-secondary">Search palette</span>
          <span class="font-mono text-fg-muted">
            <kbd class="rounded bg-surface-sunken px-1.5 py-0.5">⌘</kbd>
            <span class="mx-1">+</span>
            <kbd class="rounded bg-surface-sunken px-1.5 py-0.5">K</kbd>
          </span>
        </div>
        <div class="flex items-baseline justify-between gap-3 text-body-xs">
          <span class="text-fg-secondary">Toggle this overlay</span>
          <span class="font-mono text-fg-muted">
            <kbd class="rounded bg-surface-sunken px-1.5 py-0.5">?</kbd>
          </span>
        </div>
      </div>
      <footer class="border-t border-rule bg-surface px-4 py-2 text-body-xs text-fg-muted">
        Shortcuts disabled while typing in form fields.
      </footer>
    </div>
  </div>
{/if}
