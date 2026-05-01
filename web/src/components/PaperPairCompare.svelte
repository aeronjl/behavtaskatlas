<script lang="ts">
  /*
   * PaperPairCompare — pick any two papers from /papers and view their
   * findings overlaid on shared evidence axes plus per-axis parameter
   * deltas where both have psychometric fits.
   *
   * The component is fully client-side: the page passes in compact
   * arrays for `papers` and `findings`, and we shape the comparison
   * locally on each picker change. URL state (`?a=…&b=…`) makes the
   * view shareable and lets the picker remember its choice across
   * reloads.
   */
  import MiniFindingsChart from "./MiniFindingsChart.svelte";

  type Paper = {
    id: string;
    slug: string;
    label: string;
    year: number;
    species: string[];
  };

  type FitFields = {
    mu: number;
    sigma: number;
    gamma: number;
    lapse: number;
    threshold?: number | null;
    threshold_target_y?: number | null;
  };

  type Finding = {
    finding_id: string;
    paper_id: string;
    paper_year: number;
    paper_citation: string;
    species: string | null;
    protocol_id: string;
    protocol_name: string;
    curve_type: string;
    x_label: string;
    x_units: string | null;
    y_label: string;
    n_trials?: number | null;
    stratification?: { condition?: string | null; subject_id?: string | null };
    points: Array<{ x: number; y: number; n: number; y_lower?: number | null; y_upper?: number | null }>;
    fit?: FitFields | null;
  };

  let {
    papers,
    findings,
  }: {
    papers: Paper[];
    findings: Finding[];
  } = $props();

  function initialParam(name: string): string {
    if (typeof window === "undefined") return "";
    return new URLSearchParams(window.location.search).get(name) ?? "";
  }

  let paperA = $state(initialParam("a"));
  let paperB = $state(initialParam("b"));

  // URL sync — same shape as the FindingsOverlay sync so links remain
  // shareable. Only emits params when set.
  $effect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams();
    if (paperA) params.set("a", paperA);
    if (paperB) params.set("b", paperB);
    const qs = params.toString();
    const url = `${window.location.pathname}${qs ? `?${qs}` : ""}${window.location.hash}`;
    if (url !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      window.history.replaceState(null, "", url);
    }
  });

  const findingsByPaper = $derived.by(() => {
    const map = new Map<string, Finding[]>();
    for (const f of findings) {
      const list = map.get(f.paper_id) ?? [];
      list.push(f);
      map.set(f.paper_id, list);
    }
    return map;
  });

  const aFindings = $derived(findingsByPaper.get(paperA) ?? []);
  const bFindings = $derived(findingsByPaper.get(paperB) ?? []);

  // Group axes by (curve_type | x_label | x_units) so RDM motion vs
  // Walsh contrast don't collapse onto the same x even when both are
  // psychometric. Each group becomes one comparison row.
  type AxisGroup = {
    key: string;
    curve_type: string;
    x_label: string;
    x_units: string | null;
    fromA: Finding[];
    fromB: Finding[];
  };

  function axisKey(f: Finding): string {
    return `${f.curve_type}|${f.x_label}|${f.x_units ?? ""}`;
  }

  const sharedAxes = $derived.by<AxisGroup[]>(() => {
    if (!paperA || !paperB) return [];
    const a = new Map<string, Finding[]>();
    const b = new Map<string, Finding[]>();
    for (const f of aFindings) {
      const k = axisKey(f);
      const list = a.get(k) ?? [];
      list.push(f);
      a.set(k, list);
    }
    for (const f of bFindings) {
      const k = axisKey(f);
      const list = b.get(k) ?? [];
      list.push(f);
      b.set(k, list);
    }
    const out: AxisGroup[] = [];
    for (const [k, fromA] of a.entries()) {
      const fromB = b.get(k);
      if (!fromB) continue;
      const sample = fromA[0];
      out.push({
        key: k,
        curve_type: sample.curve_type,
        x_label: sample.x_label,
        x_units: sample.x_units,
        fromA,
        fromB,
      });
    }
    return out.sort((x, y) => x.curve_type.localeCompare(y.curve_type));
  });

  // Pick a single representative fit per paper × axis (the one with the
  // smallest stratification stratum, e.g. the "pooled" finding when one
  // exists). Used for the parameter delta table.
  function representativeFit(group: Finding[]): { entry: Finding; fit: FitFields } | null {
    const pooled = group.find(
      (f) => !f.stratification?.subject_id && f.fit && f.fit.threshold !== null && f.fit.threshold !== undefined,
    );
    if (pooled?.fit) return { entry: pooled, fit: pooled.fit };
    const any = group.find((f) => f.fit && f.fit.threshold !== null && f.fit.threshold !== undefined);
    if (any?.fit) return { entry: any, fit: any.fit };
    return null;
  }

  type AxisDelta = {
    key: string;
    label: string;
    a_label: string;
    b_label: string;
    delta_mu: number;
    delta_sigma: number;
    delta_threshold: number | null;
    a: { mu: number; sigma: number; threshold: number | null };
    b: { mu: number; sigma: number; threshold: number | null };
  };

  const deltas = $derived.by<AxisDelta[]>(() => {
    const out: AxisDelta[] = [];
    for (const group of sharedAxes) {
      if (group.curve_type !== "psychometric") continue;
      const a = representativeFit(group.fromA);
      const b = representativeFit(group.fromB);
      if (!a || !b) continue;
      const aThresh = Number.isFinite(a.fit.threshold ?? NaN) ? (a.fit.threshold as number) : null;
      const bThresh = Number.isFinite(b.fit.threshold ?? NaN) ? (b.fit.threshold as number) : null;
      out.push({
        key: group.key,
        label: `${group.x_label}${group.x_units ? ` (${group.x_units})` : ""}`,
        a_label: a.entry.paper_citation.split(".")[0] ?? a.entry.paper_id,
        b_label: b.entry.paper_citation.split(".")[0] ?? b.entry.paper_id,
        delta_mu: b.fit.mu - a.fit.mu,
        delta_sigma: b.fit.sigma - a.fit.sigma,
        delta_threshold:
          aThresh !== null && bThresh !== null ? bThresh - aThresh : null,
        a: { mu: a.fit.mu, sigma: a.fit.sigma, threshold: aThresh },
        b: { mu: b.fit.mu, sigma: b.fit.sigma, threshold: bThresh },
      });
    }
    return out;
  });

  function fmt(n: number | null, digits = 2): string {
    if (n === null || !Number.isFinite(n)) return "—";
    return n.toFixed(digits);
  }

  function combinedFindings(group: AxisGroup): Finding[] {
    return [...group.fromA, ...group.fromB];
  }
</script>

<section class="space-y-6">
  <div class="grid grid-cols-1 gap-3 md:grid-cols-2">
    <label class="block text-body-xs">
      <span class="mb-1 block font-semibold text-fg-secondary">Paper A</span>
      <select
        bind:value={paperA}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-body"
      >
        <option value="">— pick a paper —</option>
        {#each papers as paper (paper.id)}
          <option value={paper.id} disabled={paper.id === paperB}>
            {paper.label} ({paper.year})
          </option>
        {/each}
      </select>
    </label>
    <label class="block text-body-xs">
      <span class="mb-1 block font-semibold text-fg-secondary">Paper B</span>
      <select
        bind:value={paperB}
        class="w-full rounded-md border border-rule-strong bg-surface-raised px-2 py-1.5 text-body"
      >
        <option value="">— pick a paper —</option>
        {#each papers as paper (paper.id)}
          <option value={paper.id} disabled={paper.id === paperA}>
            {paper.label} ({paper.year})
          </option>
        {/each}
      </select>
    </label>
  </div>

  {#if !paperA || !paperB}
    <div
      class="rounded-md border border-dashed border-rule-strong bg-surface p-6 text-center text-body text-fg-secondary"
    >
      Pick two papers to overlay their findings on shared evidence axes.
    </div>
  {:else if sharedAxes.length === 0}
    <div
      class="rounded-md border border-rule bg-surface-raised p-6 text-body text-fg-secondary"
    >
      <p class="mb-2 font-semibold">No shared evidence axes.</p>
      <p class="text-body-xs text-fg-muted">
        Both papers have curated findings, but none of them share a
        (<code class="rounded bg-surface-sunken px-1 text-mono-id">curve_type</code>,
        <code class="rounded bg-surface-sunken px-1 text-mono-id">x_label</code>,
        <code class="rounded bg-surface-sunken px-1 text-mono-id">x_units</code>)
        triple — the atlas keeps incompatible stimulus axes apart on
        purpose. Try a different pair.
      </p>
    </div>
  {:else}
    <p class="text-body-xs text-fg-muted animate-fade-in">
      <span class="font-mono text-fg">{sharedAxes.length}</span> shared
      axis{sharedAxes.length === 1 ? "" : "es"} between the two papers.
    </p>

    {#if deltas.length > 0}
      <section class="rounded-md border border-rule bg-surface-raised p-4 animate-fade-in">
        <header class="mb-3 flex items-baseline justify-between gap-3">
          <div>
            <p class="text-eyebrow uppercase text-fg-muted">Parameter deltas</p>
            <h3 class="mt-1 text-h3 text-fg">B − A on shared psychometric axes</h3>
          </div>
        </header>
        <p class="mb-3 max-w-prose text-body-xs text-fg-secondary">
          Pooled-curve fits are preferred when a paper has them; otherwise
          the per-condition fit with the most coverage stands in.
          Threshold = x at the curve's target y (75% on most psychometrics).
        </p>
        <div class="overflow-x-auto rounded border border-rule">
          <table class="w-full text-body-xs">
            <thead class="bg-surface text-left text-eyebrow uppercase text-fg-muted">
              <tr>
                <th class="px-3 py-2">Axis</th>
                <th class="px-3 py-2 text-right">A · μ</th>
                <th class="px-3 py-2 text-right">B · μ</th>
                <th class="px-3 py-2 text-right">Δ μ</th>
                <th class="px-3 py-2 text-right">A · σ</th>
                <th class="px-3 py-2 text-right">B · σ</th>
                <th class="px-3 py-2 text-right">Δ σ</th>
                <th class="px-3 py-2 text-right">A · thr</th>
                <th class="px-3 py-2 text-right">B · thr</th>
                <th class="px-3 py-2 text-right">Δ thr</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-rule">
              {#each deltas as d (d.key)}
                <tr>
                  <td class="px-3 py-2 text-fg">{d.label}</td>
                  <td class="px-3 py-2 text-right font-mono">{fmt(d.a.mu)}</td>
                  <td class="px-3 py-2 text-right font-mono">{fmt(d.b.mu)}</td>
                  <td class="px-3 py-2 text-right font-mono font-semibold text-fg">
                    {fmt(d.delta_mu)}
                  </td>
                  <td class="px-3 py-2 text-right font-mono">{fmt(d.a.sigma)}</td>
                  <td class="px-3 py-2 text-right font-mono">{fmt(d.b.sigma)}</td>
                  <td class="px-3 py-2 text-right font-mono font-semibold text-fg">
                    {fmt(d.delta_sigma)}
                  </td>
                  <td class="px-3 py-2 text-right font-mono">{fmt(d.a.threshold)}</td>
                  <td class="px-3 py-2 text-right font-mono">{fmt(d.b.threshold)}</td>
                  <td class="px-3 py-2 text-right font-mono font-semibold text-fg">
                    {fmt(d.delta_threshold)}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    <div class="space-y-6">
      {#each sharedAxes as group (group.key)}
        <article class="rounded-md border border-rule bg-surface-raised p-4 animate-fade-in">
          <header class="mb-3">
            <p class="text-eyebrow uppercase text-fg-muted">
              {group.curve_type.replace(/_/g, " ")}
            </p>
            <h3 class="mt-1 text-h3 text-fg">
              {group.x_label}{group.x_units ? ` (${group.x_units})` : ""}
            </h3>
            <p class="mt-1 text-body-xs text-fg-muted">
              <span class="font-mono">{group.fromA.length}</span> finding{group.fromA.length === 1 ? "" : "s"} from A ·
              <span class="font-mono">{group.fromB.length}</span> finding{group.fromB.length === 1 ? "" : "s"} from B
            </p>
          </header>
          <MiniFindingsChart
            findings={combinedFindings(group)}
            colorBy="paper"
            height={280}
            showTraceControls={false}
          />
        </article>
      {/each}
    </div>
  {/if}
</section>
