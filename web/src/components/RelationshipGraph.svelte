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
  const TYPE_COLORS: Record<string, string> = {
    task_family: "#7c3aed",
    protocol: "#2b5ea0",
    dataset: "#246b3b",
    vertical_slice: "#b35c00",
  };

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
  let layoutTick = $state(0);

  $effect(() => {
    // Re-run simulation any time inputs or width change.
    void simNodes;
    void simEdges;
    void width;

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

  function dimNode(node: SimNode): boolean {
    if (activeType && node.node_type !== activeType) return true;
    if (hoveredNodeId) {
      if (node.node_id === hoveredNodeId) return false;
      const neighbors = adjacency.get(hoveredNodeId);
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
    if (hoveredNodeId) {
      return (
        edge.source.node_id !== hoveredNodeId &&
        edge.target.node_id !== hoveredNodeId
      );
    }
    return false;
  }

  function nodeRadius(node: SimNode): number {
    return hoveredNodeId === node.node_id ? 8 : 6;
  }

  function clamp(value: number | undefined, min: number, max: number): number {
    if (value === undefined || !Number.isFinite(value)) return (min + max) / 2;
    return Math.max(min, Math.min(max, value));
  }
</script>

<div bind:this={containerEl} class="relative">
  <div class="mb-3 flex flex-wrap items-center gap-2 text-xs">
    <span class="text-slate-500">Filter:</span>
    {#each TYPE_ORDER as type (type)}
      {@const isActive = activeType === type}
      <button
        type="button"
        class:list={[
          "inline-flex items-center gap-1.5 rounded border px-2 py-1",
          isActive
            ? "border-slate-900 bg-slate-900 text-white"
            : "border-slate-300 bg-white text-slate-700 hover:border-accent",
        ]}
        onclick={() => (activeType = isActive ? null : type)}
      >
        <span
          class="inline-block h-2 w-2 rounded-full"
          style={`background-color: ${TYPE_COLORS[type]}`}
          aria-hidden="true"
        ></span>
        {TYPE_LABELS[type]}
      </button>
    {/each}
    {#if hoveredNodeId}
      <span class="ml-auto font-mono text-[11px] text-slate-500">
        {hoveredNodeId}
      </span>
    {/if}
  </div>

  <div class="overflow-hidden rounded-md border border-slate-200 bg-white">
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
              stroke={dimEdge(edge) ? "#e2e8f0" : "#94a3b8"}
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
            {@const color = TYPE_COLORS[node.node_type] ?? "#64748b"}
            <g
              transform={`translate(${cx}, ${cy})`}
              opacity={dim ? 0.25 : 1}
              onmouseenter={() => (hoveredNodeId = node.node_id)}
              onmouseleave={() => (hoveredNodeId = null)}
              onfocus={() => (hoveredNodeId = node.node_id)}
              onblur={() => (hoveredNodeId = null)}
              tabindex="0"
              role="button"
              aria-label={node.label}
              style="cursor: pointer; outline: none;"
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
              <circle
                r={nodeRadius(node) + 2}
                fill="white"
                stroke={color}
                stroke-width="2"
              />
              <circle r={nodeRadius(node)} fill={color} />
              {#if hoveredNodeId === node.node_id || (!hoveredNodeId && !activeType)}
                <text
                  x={nodeRadius(node) + 5}
                  y="4"
                  font-size="10"
                  fill="#0f172a"
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
  <p class="mt-2 text-[11px] text-slate-500">
    {simNodes.length} nodes · {simEdges.length} edges. Hover a node to highlight
    its neighbours; click to navigate to its detail page. Use the filter chips
    above to isolate a record type.
  </p>
</div>
