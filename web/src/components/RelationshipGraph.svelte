<script lang="ts">
  import {
    forceCenter,
    forceCollide,
    forceLink,
    forceManyBody,
    forceSimulation,
    forceX,
    forceY,
  } from "d3-force";
  import { chartChrome, nodeColors } from "../lib/encoding";

  type GraphNode = {
    node_id: string;
    label: string;
    node_type: string;
    status?: string;
    href?: string | null;
  };

  type GraphEdge = {
    source: string;
    target: string;
    label: string;
  };

  interface Props {
    nodes: GraphNode[];
    edges: GraphEdge[];
    height?: number;
  }

  let { nodes, edges, height = 600 }: Props = $props();

  type SimNode = GraphNode & {
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
    fx?: number | null;
    fy?: number | null;
    index?: number;
  };

  type SimEdge = {
    source: SimNode;
    target: SimNode;
    label: string;
  };

  const TYPE_ORDER = ["task_family", "protocol", "dataset", "vertical_slice"];
  const TYPE_LABELS: Record<string, string> = {
    task_family: "Task family",
    protocol: "Protocol",
    dataset: "Dataset",
    vertical_slice: "Slice",
  };
  // SSR fallbacks; refreshed on client mount via $effect so the live
  // CSS-variable values flow into rendered SVG attributes.
  let chrome = $state(chartChrome());
  let typeColors = $state(nodeColors());

  $effect(() => {
    chrome = chartChrome();
    typeColors = nodeColors();
  });

  let containerEl: HTMLDivElement | null = $state(null);
  let width = $state(900);
  const padding = 24;

  $effect(() => {
    if (!containerEl) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (w > 0) width = Math.max(320, Math.floor(w));
      }
    });
    observer.observe(containerEl);
    return () => observer.disconnect();
  });

  const simNodes: SimNode[] = $derived.by(() =>
    nodes.map((n) => ({ ...n })),
  );

  const nodesById = $derived.by(() => new Map(simNodes.map((n) => [n.node_id, n])));

  const simEdges: SimEdge[] = $derived.by(() =>
    edges
      .map((e) => {
        const source = nodesById.get(e.source);
        const target = nodesById.get(e.target);
        if (!source || !target) return null;
        return { source, target, label: e.label };
      })
      .filter((e): e is SimEdge => e !== null),
  );

  let activeType = $state<string | null>(null);
  let hoveredNodeId = $state<string | null>(null);
  let focusedNodeId = $state<string | null>(null);
  let layoutTick = $state(0);

  // Honor prefers-reduced-motion: when set, skip the d3-force animation
  // and snap to the static column layout. The reactive flag lets users
  // toggle the OS preference and have the next layout pass respect it.
  let reduceMotion = $state(false);
  $effect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    reduceMotion = mq.matches;
    const handler = (event: MediaQueryListEvent) => {
      reduceMotion = event.matches;
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  });

  $effect(() => {
    // Re-run simulation any time inputs or width change.
    void simNodes;
    void simEdges;
    void width;
    void reduceMotion;

    if (simNodes.length === 0) return;

    // Initial spread by type column to give the simulation a stable start.
    const groups = new Map<string, SimNode[]>();
    for (const node of simNodes) {
      const list = groups.get(node.node_type) ?? [];
      list.push(node);
      groups.set(node.node_type, list);
    }
    const columnX = (type: string) => {
      const idx = Math.max(0, TYPE_ORDER.indexOf(type));
      return padding + ((width - padding * 2) * (idx + 0.5)) / TYPE_ORDER.length;
    };
    for (const [type, list] of groups) {
      const cx = columnX(type);
      list.forEach((node, i) => {
        node.x = cx + (Math.random() - 0.5) * 40;
        node.y =
          padding +
          ((height - padding * 2) * (i + 0.5)) / Math.max(1, list.length);
      });
    }

    if (reduceMotion) {
      // Static layout: pin each node to its column position with a
      // deterministic vertical stagger; no simulation, no animation.
      layoutTick = layoutTick + 1;
      return;
    }

    const simulation = forceSimulation<SimNode>(simNodes)
      .force(
        "link",
        forceLink<SimNode, SimEdge>(simEdges)
          .id((d) => d.node_id)
          .distance(90)
          .strength(0.4),
      )
      .force("charge", forceManyBody<SimNode>().strength(-220))
      .force("collide", forceCollide<SimNode>().radius(28))
      .force(
        "x",
        forceX<SimNode>((d) => columnX(d.node_type)).strength(0.18),
      )
      .force("y", forceY<SimNode>(height / 2).strength(0.04))
      .force("center", forceCenter(width / 2, height / 2).strength(0.02))
      .alpha(1)
      .alphaDecay(0.05);

    simulation.on("tick", () => {
      layoutTick = layoutTick + 1;
    });

    return () => simulation.stop();
  });

  const adjacency = $derived.by(() => {
    const map = new Map<string, Set<string>>();
    for (const edge of simEdges) {
      const a = edge.source.node_id;
      const b = edge.target.node_id;
      if (!map.has(a)) map.set(a, new Set());
      if (!map.has(b)) map.set(b, new Set());
      map.get(a)!.add(b);
      map.get(b)!.add(a);
    }
    return map;
  });

  // The "active" node for highlight/focus purposes — hover wins; falls
  // back to keyboard focus so tabbing through nodes lights up the same
  // neighbour subgraph that hovering does.
  const activeNodeId = $derived(hoveredNodeId ?? focusedNodeId);

  function dimNode(node: SimNode): boolean {
    if (activeType && node.node_type !== activeType) return true;
    if (activeNodeId) {
      if (node.node_id === activeNodeId) return false;
      const neighbors = adjacency.get(activeNodeId);
      if (!neighbors || !neighbors.has(node.node_id)) return true;
    }
    return false;
  }

  function dimEdge(edge: SimEdge): boolean {
    if (
      activeType &&
      edge.source.node_type !== activeType &&
      edge.target.node_type !== activeType
    )
      return true;
    if (activeNodeId) {
      return (
        edge.source.node_id !== activeNodeId &&
        edge.target.node_id !== activeNodeId
      );
    }
    return false;
  }

  function nodeRadius(node: SimNode): number {
    return activeNodeId === node.node_id ? 8 : 6;
  }

  function clamp(value: number | undefined, min: number, max: number): number {
    if (value === undefined || !Number.isFinite(value)) return (min + max) / 2;
    return Math.max(min, Math.min(max, value));
  }
</script>

<div bind:this={containerEl} class="relative">
  <div class="mb-3 flex flex-wrap items-center gap-2 text-body-xs">
    <span class="text-fg-muted">Filter:</span>
    {#each TYPE_ORDER as type (type)}
      {@const isActive = activeType === type}
      <button
        type="button"
        aria-pressed={isActive}
        class={[
          "inline-flex items-center gap-1.5 rounded border px-2 py-1",
          isActive
            ? "border-fg bg-fg text-fg-inverse"
            : "border-rule-strong bg-surface-raised text-fg-secondary hover:border-rule-emphasis",
        ]}
        onclick={() => (activeType = isActive ? null : type)}
      >
        <span
          class="inline-block h-2 w-2 rounded-full"
          style={`background-color: ${typeColors[type] ?? chrome.mutedFg}`}
          aria-hidden="true"
        ></span>
        {TYPE_LABELS[type]}
      </button>
    {/each}
    {#if activeNodeId}
      <span class="ml-auto font-mono text-mono-id text-fg-muted">
        {activeNodeId}
      </span>
    {/if}
  </div>

  <div class="overflow-hidden rounded-md border border-rule bg-surface-raised">
    {#key layoutTick}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={height}
        role="img"
        aria-label="Relationship graph across task families, protocols, datasets, and slices"
      >
        <g>
          {#each simEdges as edge (edge.source.node_id + "->" + edge.target.node_id)}
            <line
              x1={clamp(edge.source.x, padding, width - padding)}
              y1={clamp(edge.source.y, padding, height - padding)}
              x2={clamp(edge.target.x, padding, width - padding)}
              y2={clamp(edge.target.y, padding, height - padding)}
              stroke={dimEdge(edge) ? chrome.gridColor : chrome.subtleFg}
              stroke-width={dimEdge(edge) ? 0.8 : 1.2}
              opacity={dimEdge(edge) ? 0.4 : 0.9}
            />
          {/each}
        </g>
        <g>
          {#each simNodes as node (node.node_id)}
            {@const cx = clamp(node.x, padding, width - padding)}
            {@const cy = clamp(node.y, padding, height - padding)}
            {@const dim = dimNode(node)}
            {@const color = typeColors[node.node_type] ?? chrome.mutedFg}
            {@const focused = focusedNodeId === node.node_id}
            <g
              class="graph-node"
              transform={`translate(${cx}, ${cy})`}
              opacity={dim ? 0.25 : 1}
              onmouseenter={() => (hoveredNodeId = node.node_id)}
              onmouseleave={() => (hoveredNodeId = null)}
              onfocus={() => (focusedNodeId = node.node_id)}
              onblur={() => (focusedNodeId = null)}
              tabindex="0"
              role="button"
              aria-label={node.label}
              onkeydown={(event) => {
                if ((event.key === "Enter" || event.key === " ") && node.href) {
                  event.preventDefault();
                  window.location.href = node.href;
                }
              }}
              onclick={() => {
                if (node.href) window.location.href = node.href;
              }}
            >
              {#if focused}
                <circle
                  class="graph-node-focus-halo"
                  r={nodeRadius(node) + 6}
                  fill="none"
                  stroke={chrome.titleColor}
                  stroke-width="2"
                />
              {/if}
              <circle
                r={nodeRadius(node) + 2}
                fill="white"
                stroke={color}
                stroke-width="2"
              />
              <circle r={nodeRadius(node)} fill={color} />
              {#if activeNodeId === node.node_id || (!activeNodeId && !activeType)}
                <text
                  x={nodeRadius(node) + 5}
                  y="4"
                  font-size="10"
                  fill={chrome.titleColor}
                  font-family="-apple-system, BlinkMacSystemFont, sans-serif"
                >
                  {node.label.length > 28 ? node.label.slice(0, 27) + "…" : node.label}
                </text>
              {/if}
            </g>
          {/each}
        </g>
      </svg>
    {/key}
  </div>
  <p class="mt-2 text-mono-id text-fg-muted">
    {simNodes.length} nodes · {simEdges.length} edges. Hover or tab to a node
    to highlight its neighbours; press Enter to open its detail page. Use the
    filter chips above to isolate a record type.
  </p>
</div>

<style>
  /* Default: SVG focus rings draw a hard browser outline around the
   * <g>'s axis-aligned bounding box, which doesn't match the circular
   * node. Suppress the default and rely on the rendered focus halo
   * (drawn as an SVG circle in the markup above) for the focus
   * indicator. The halo only renders on :focus-visible-equivalent
   * keyboard focus because focusedNodeId is set in onfocus. */
  .graph-node {
    cursor: pointer;
    outline: none;
  }
  .graph-node:focus-visible {
    outline: none;
  }
</style>
