<script lang="ts">
  /*
   * Layered relationship graph.
   *
   * Replaces an earlier d3-force layout with a deterministic
   * column-per-type stack: task_family → protocol → dataset →
   * vertical_slice. Each column lays its nodes out vertically in
   * alphabetical order so the same input always produces the same
   * picture (no animation on first paint, no shift on filter).
   *
   * Two interactive affordances above the static layout:
   *
   * - **Search** dims non-matching nodes; partial label match.
   * - **Path mode** lets a user click two nodes and surfaces the
   *   shortest connecting path via BFS over the (undirected) edge
   *   set, highlighting both nodes and edges on the chain. In
   *   navigate mode (the default) clicking a node opens its detail
   *   page; the mode toggle keeps the two interactions disambiguated.
   */

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

  let { nodes, edges, height = 620 }: Props = $props();

  const TYPE_ORDER = ["task_family", "protocol", "dataset", "vertical_slice"];
  const TYPE_LABELS: Record<string, string> = {
    task_family: "Task family",
    protocol: "Protocol",
    dataset: "Dataset",
    vertical_slice: "Slice",
  };

  let chrome = $state(chartChrome());
  let typeColors = $state(nodeColors());

  $effect(() => {
    chrome = chartChrome();
    typeColors = nodeColors();
  });

  let containerEl: HTMLDivElement | null = $state(null);
  let width = $state(900);
  const padding = { left: 24, right: 24, top: 24, bottom: 24 };

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

  // ── Static layered layout ───────────────────────────────────────────────

  const nodesByType = $derived.by(() => {
    const groups = new Map<string, GraphNode[]>();
    for (const type of TYPE_ORDER) groups.set(type, []);
    for (const node of nodes) {
      const list = groups.get(node.node_type);
      if (list) list.push(node);
      else {
        // Unknown type — collect under a synthetic "other" column at end.
        const other = groups.get("other") ?? [];
        other.push(node);
        groups.set("other", other);
      }
    }
    for (const list of groups.values()) {
      list.sort((a, b) => a.label.localeCompare(b.label));
    }
    return groups;
  });

  type LayoutNode = GraphNode & { x: number; y: number };

  const layout = $derived.by(() => {
    const result = new Map<string, LayoutNode>();
    const columns = TYPE_ORDER.filter((t) => (nodesByType.get(t)?.length ?? 0) > 0);
    if (columns.length === 0) return result;
    const colWidth = (width - padding.left - padding.right) / columns.length;
    columns.forEach((type, colIndex) => {
      const list = nodesByType.get(type) ?? [];
      const cx = padding.left + colWidth * (colIndex + 0.5);
      const usableHeight = height - padding.top - padding.bottom;
      const rowGap =
        list.length <= 1 ? 0 : usableHeight / (list.length - 1);
      list.forEach((node, rowIndex) => {
        const y =
          list.length === 1
            ? height / 2
            : padding.top + rowGap * rowIndex;
        result.set(node.node_id, { ...node, x: cx, y });
      });
    });
    return result;
  });

  type LayoutEdge = {
    source: LayoutNode;
    target: LayoutNode;
    label: string;
  };

  const layoutEdges = $derived.by(() => {
    const result: LayoutEdge[] = [];
    for (const edge of edges) {
      const source = layout.get(edge.source);
      const target = layout.get(edge.target);
      if (source && target) {
        result.push({ source, target, label: edge.label });
      }
    }
    return result;
  });

  // Adjacency map for hover-neighbour highlight + BFS path-finding.
  const adjacency = $derived.by(() => {
    const map = new Map<string, Set<string>>();
    for (const edge of layoutEdges) {
      const a = edge.source.node_id;
      const b = edge.target.node_id;
      if (!map.has(a)) map.set(a, new Set());
      if (!map.has(b)) map.set(b, new Set());
      map.get(a)!.add(b);
      map.get(b)!.add(a);
    }
    return map;
  });

  // ── Filter / search / interaction state ─────────────────────────────────

  let activeType = $state<string | null>(null);
  let searchText = $state("");
  let hoveredNodeId = $state<string | null>(null);
  let focusedNodeId = $state<string | null>(null);
  type Mode = "navigate" | "path";
  let mode = $state<Mode>("navigate");
  let pathSource = $state<string | null>(null);
  let pathTarget = $state<string | null>(null);

  const activeNodeId = $derived(hoveredNodeId ?? focusedNodeId);

  const searchTokens = $derived(
    searchText
      .toLowerCase()
      .split(/\s+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0),
  );

  function nodeMatches(node: GraphNode): boolean {
    if (searchTokens.length === 0) return true;
    const haystack = `${node.label} ${node.node_id}`.toLowerCase();
    return searchTokens.every((token) => haystack.includes(token));
  }

  // BFS shortest path between source and target. Returns the ordered
  // node IDs along the path, or null if disconnected. Symmetric in
  // (source, target) since the edge graph is undirected for navigation.
  function shortestPath(
    source: string | null,
    target: string | null,
  ): string[] | null {
    if (!source || !target || source === target) return null;
    const visited = new Map<string, string | null>();
    visited.set(source, null);
    const queue: string[] = [source];
    while (queue.length > 0) {
      const node = queue.shift()!;
      if (node === target) {
        const path: string[] = [];
        let cursor: string | null = node;
        while (cursor !== null) {
          path.unshift(cursor);
          cursor = visited.get(cursor) ?? null;
        }
        return path;
      }
      const neighbors = adjacency.get(node);
      if (!neighbors) continue;
      for (const next of neighbors) {
        if (!visited.has(next)) {
          visited.set(next, node);
          queue.push(next);
        }
      }
    }
    return null;
  }

  const pathNodes = $derived.by(() => shortestPath(pathSource, pathTarget));

  const pathEdgeKeys = $derived.by(() => {
    if (!pathNodes || pathNodes.length < 2) return new Set<string>();
    const keys = new Set<string>();
    for (let i = 0; i < pathNodes.length - 1; i++) {
      // Both directions stored — the rendering side checks both.
      keys.add(`${pathNodes[i]}|${pathNodes[i + 1]}`);
      keys.add(`${pathNodes[i + 1]}|${pathNodes[i]}`);
    }
    return keys;
  });

  function clearPath() {
    pathSource = null;
    pathTarget = null;
  }

  function onNodeClick(node: GraphNode) {
    if (mode === "path") {
      if (!pathSource) {
        pathSource = node.node_id;
        return;
      }
      if (!pathTarget && node.node_id !== pathSource) {
        pathTarget = node.node_id;
        return;
      }
      // Third click resets to picking again from this node.
      pathSource = node.node_id;
      pathTarget = null;
      return;
    }
    if (node.href) {
      window.location.href = node.href;
    }
  }

  function setMode(next: Mode) {
    mode = next;
    if (mode !== "path") clearPath();
  }

  // Visibility computations: a node is dim if filtered-out by type or
  // search; or if a node is hovered/focused, only its neighbors stay
  // bright; or if a path is rendered, only path nodes stay bright.
  function dimNode(node: GraphNode): boolean {
    if (activeType && node.node_type !== activeType) return true;
    if (!nodeMatches(node)) return true;
    if (pathNodes && pathNodes.length > 0) {
      return !pathNodes.includes(node.node_id);
    }
    if (activeNodeId) {
      if (node.node_id === activeNodeId) return false;
      const neighbors = adjacency.get(activeNodeId);
      if (!neighbors || !neighbors.has(node.node_id)) return true;
    }
    return false;
  }

  function dimEdge(edge: LayoutEdge): boolean {
    if (
      activeType &&
      edge.source.node_type !== activeType &&
      edge.target.node_type !== activeType
    )
      return true;
    if (!nodeMatches(edge.source) && !nodeMatches(edge.target)) return true;
    if (pathEdgeKeys.size > 0) {
      const key = `${edge.source.node_id}|${edge.target.node_id}`;
      return !pathEdgeKeys.has(key);
    }
    if (activeNodeId) {
      return (
        edge.source.node_id !== activeNodeId &&
        edge.target.node_id !== activeNodeId
      );
    }
    return false;
  }

  function nodeRadius(node: GraphNode): number {
    if (pathNodes && pathNodes.includes(node.node_id)) return 8;
    if (pathSource === node.node_id || pathTarget === node.node_id) return 9;
    return activeNodeId === node.node_id ? 8 : 6;
  }

  function isSelectedForPath(node: GraphNode): boolean {
    return pathSource === node.node_id || pathTarget === node.node_id;
  }

  // Cubic-bezier curve from source to target, biased so connections
  // between adjacent columns flow horizontally before bending.
  function edgePath(edge: LayoutEdge): string {
    const dx = edge.target.x - edge.source.x;
    const c1x = edge.source.x + dx * 0.5;
    const c2x = edge.target.x - dx * 0.5;
    return `M ${edge.source.x} ${edge.source.y} C ${c1x} ${edge.source.y}, ${c2x} ${edge.target.y}, ${edge.target.x} ${edge.target.y}`;
  }

  const visibleColumns = $derived(
    TYPE_ORDER.filter((t) => (nodesByType.get(t)?.length ?? 0) > 0),
  );
  const columnHeaderY = padding.top - 6;
  function columnX(type: string): number {
    const idx = visibleColumns.indexOf(type);
    if (idx < 0) return width / 2;
    const colWidth =
      (width - padding.left - padding.right) / visibleColumns.length;
    return padding.left + colWidth * (idx + 0.5);
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
    <label class="ml-2 inline-flex items-center gap-1 text-fg-muted">
      <span class="sr-only">Search nodes</span>
      <input
        type="search"
        bind:value={searchText}
        placeholder="Search labels…"
        class="rounded-md border border-rule-strong bg-surface-raised px-2 py-0.5 text-body-xs text-fg-secondary focus:border-rule-emphasis focus:outline-none focus:ring-1 focus:ring-accent"
      />
    </label>
    <fieldset
      class="ml-auto flex items-center gap-1 rounded border border-rule-strong p-0.5"
    >
      <legend class="sr-only">Click mode</legend>
      <button
        type="button"
        aria-pressed={mode === "navigate"}
        class={[
          "rounded px-2 py-0.5 text-body-xs",
          mode === "navigate"
            ? "bg-accent text-fg-inverse"
            : "text-fg-secondary hover:text-accent",
        ]}
        onclick={() => setMode("navigate")}
      >
        Navigate
      </button>
      <button
        type="button"
        aria-pressed={mode === "path"}
        class={[
          "rounded px-2 py-0.5 text-body-xs",
          mode === "path"
            ? "bg-accent text-fg-inverse"
            : "text-fg-secondary hover:text-accent",
        ]}
        onclick={() => setMode("path")}
        title="Click two nodes to highlight the shortest path between them."
      >
        Find path
      </button>
    </fieldset>
  </div>

  {#if mode === "path"}
    <p class="mb-2 text-body-xs text-fg-muted animate-fade-in">
      {#if !pathSource}
        Click any node to mark the start.
      {:else if !pathTarget}
        Start: <span class="font-mono text-fg">{layout.get(pathSource)?.label ?? pathSource}</span>.
        Click another node to find the path.
      {:else if pathNodes}
        Path: <span class="font-mono text-fg">{pathNodes.length - 1}</span> hop{pathNodes.length - 1 === 1 ? "" : "s"} from
        <span class="font-mono text-fg">{layout.get(pathSource)?.label ?? pathSource}</span> to
        <span class="font-mono text-fg">{layout.get(pathTarget)?.label ?? pathTarget}</span>.
        <button
          type="button"
          class="ml-2 text-accent hover:underline"
          onclick={clearPath}
        >Reset</button>
      {:else}
        No path between
        <span class="font-mono text-fg">{layout.get(pathSource)?.label ?? pathSource}</span>
        and
        <span class="font-mono text-fg">{layout.get(pathTarget)?.label ?? pathTarget}</span>.
        <button
          type="button"
          class="ml-2 text-accent hover:underline"
          onclick={clearPath}
        >Reset</button>
      {/if}
    </p>
  {/if}

  <div class="overflow-hidden rounded-md border border-rule bg-surface-raised">
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      role="img"
      aria-label="Layered relationship graph across task families, protocols, datasets, and slices"
    >
      <g>
        {#each visibleColumns as type (type)}
          <text
            x={columnX(type)}
            y={columnHeaderY}
            text-anchor="middle"
            font-size="10"
            font-family="-apple-system, BlinkMacSystemFont, sans-serif"
            font-weight="600"
            letter-spacing="1"
            fill={chrome.mutedFg}
          >
            {(TYPE_LABELS[type] ?? type).toUpperCase()}
          </text>
        {/each}
      </g>
      <g>
        {#each layoutEdges as edge (edge.source.node_id + "->" + edge.target.node_id)}
          {@const dim = dimEdge(edge)}
          {@const onPath =
            pathEdgeKeys.size > 0 &&
            pathEdgeKeys.has(`${edge.source.node_id}|${edge.target.node_id}`)}
          <path
            d={edgePath(edge)}
            fill="none"
            stroke={onPath ? chrome.titleColor : dim ? chrome.gridColor : chrome.subtleFg}
            stroke-width={onPath ? 2 : dim ? 0.7 : 1.2}
            opacity={dim ? 0.35 : 0.9}
          />
        {/each}
      </g>
      <g>
        {#each [...layout.values()] as node (node.node_id)}
          {@const dim = dimNode(node)}
          {@const color = typeColors[node.node_type] ?? chrome.mutedFg}
          {@const focused = focusedNodeId === node.node_id}
          {@const selected = isSelectedForPath(node)}
          <g
            class="graph-node"
            transform={`translate(${node.x}, ${node.y})`}
            opacity={dim ? 0.22 : 1}
            onmouseenter={() => (hoveredNodeId = node.node_id)}
            onmouseleave={() => (hoveredNodeId = null)}
            onfocus={() => (focusedNodeId = node.node_id)}
            onblur={() => (focusedNodeId = null)}
            tabindex="0"
            role="button"
            aria-label={node.label}
            onkeydown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onNodeClick(node);
              }
            }}
            onclick={() => onNodeClick(node)}
          >
            {#if focused || selected}
              <circle
                class="graph-node-focus-halo"
                r={nodeRadius(node) + 6}
                fill="none"
                stroke={selected ? color : chrome.titleColor}
                stroke-width={selected ? 2.5 : 2}
              />
            {/if}
            <circle
              r={nodeRadius(node) + 2}
              fill="white"
              stroke={color}
              stroke-width={selected ? 2.5 : 2}
            />
            <circle r={nodeRadius(node)} fill={color} />
            {#if activeNodeId === node.node_id || selected || (pathNodes && pathNodes.includes(node.node_id)) || (!activeNodeId && !activeType && searchTokens.length === 0)}
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
  </div>
  <p class="mt-2 text-mono-id text-fg-muted">
    {layout.size} node{layout.size === 1 ? "" : "s"} ·
    {layoutEdges.length} edge{layoutEdges.length === 1 ? "" : "s"}.
    {#if mode === "navigate"}
      Tab or hover a node to highlight neighbours; press Enter or click to open
      its detail page. Use Find path to trace the shortest connection between
      two nodes.
    {:else}
      In Find path mode: click a start, then any other node, to highlight the
      shortest connecting chain. Switch back to Navigate to open detail pages.
    {/if}
  </p>
</div>

<style>
  .graph-node {
    cursor: pointer;
    outline: none;
  }
  .graph-node:focus-visible {
    outline: none;
  }
</style>
