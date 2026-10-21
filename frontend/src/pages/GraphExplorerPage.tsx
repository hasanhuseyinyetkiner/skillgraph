import { useQuery } from "@tanstack/react-query";
import cytoscape from "cytoscape";
import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "../api";
import { Card, ErrorState, LoadingState, PageIntro } from "../components/ui";
import type { GraphPayload } from "../types";

const KIND_COLOR: Record<string, string> = {
  skill: "#C026D3",
  role: "#0F766E",
  resource: "#BE185D",
};

const EDGE_COLOR: Record<string, string> = {
  prerequisite: "#A21CAF",
  related: "#64748B",
  broader: "#0D9488",
  narrower: "#DB2777",
};

type CyInstance = ReturnType<typeof cytoscape>;
type CyDataEle = { data: (k: string) => string };

type AdjacencyRow = {
  id: string;
  label: string;
  kind: string;
  type: string;
  direction: "out" | "in";
  weight: number;
};

export function GraphExplorerPage() {
  const [category, setCategory] = useState("");
  const [relationFilter, setRelationFilter] = useState("");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<CyInstance | null>(null);

  const graph = useQuery({
    queryKey: ["graph", category, query],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "220" });
      if (category) params.set("category", category);
      if (query.trim()) params.set("q", query.trim());
      return api<GraphPayload>(`/api/graph?${params.toString()}`);
    },
  });

  const taxonomy = useMemo(() => {
    if (!graph.data) return [];
    const counts = new Map<string, number>();
    for (const node of graph.data.nodes) {
      if (node.kind !== "skill") continue;
      const cat = String(node.category ?? "uncategorized");
      counts.set(cat, (counts.get(cat) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [graph.data]);

  const selectedNode = useMemo(() => {
    if (!graph.data || !selectedId) return null;
    return graph.data.nodes.find((n) => n.id === selectedId) ?? null;
  }, [graph.data, selectedId]);

  const adjacency = useMemo((): AdjacencyRow[] => {
    if (!graph.data || !selectedId) return [];
    const byId = new Map(graph.data.nodes.map((n) => [n.id, n]));
    const rows: AdjacencyRow[] = [];
    for (const edge of graph.data.edges) {
      if (relationFilter && edge.type !== relationFilter) continue;
      if (edge.source === selectedId) {
        const target = byId.get(edge.target);
        if (!target) continue;
        rows.push({
          id: edge.id,
          label: target.label,
          kind: target.kind,
          type: edge.type,
          direction: "out",
          weight: edge.weight,
        });
      } else if (edge.target === selectedId) {
        const source = byId.get(edge.source);
        if (!source) continue;
        rows.push({
          id: edge.id,
          label: source.label,
          kind: source.kind,
          type: edge.type,
          direction: "in",
          weight: edge.weight,
        });
      }
    }
    return rows.sort((a, b) => a.type.localeCompare(b.type) || a.label.localeCompare(b.label));
  }, [graph.data, selectedId, relationFilter]);

  useEffect(() => {
    if (!graph.data || !containerRef.current) return;

    const elements = [
      ...graph.data.nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          kind: node.kind,
          category: node.category ?? "",
        },
      })),
      ...graph.data.edges
        .filter((edge) => !relationFilter || edge.type === relationFilter)
        .map((edge) => ({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.type,
            type: edge.type,
            weight: edge.weight,
          },
        })),
    ];

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            color: "#fff",
            "background-color": (ele: CyDataEle) => KIND_COLOR[ele.data("kind")] ?? "#9333EA",
            "font-size": 9,
            "font-family": "IBM Plex Sans, sans-serif",
            "text-valign": "center",
            "text-halign": "center",
            width: 30,
            height: 30,
            "text-wrap": "wrap",
            "text-max-width": 72,
            "border-width": 0,
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#F5D0FE",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.4,
            "line-color": (ele: CyDataEle) => EDGE_COLOR[ele.data("type")] ?? "#94A3B8",
            "target-arrow-color": (ele: CyDataEle) => EDGE_COLOR[ele.data("type")] ?? "#94A3B8",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 7,
            "font-family": "IBM Plex Mono, monospace",
            color: "#cbd5e1",
          },
        },
      ],
      layout: { name: "cose", animate: false, padding: 28 },
    });

    cy.on("tap", "node", (evt: { target: { id: () => string } }) => {
      setSelectedId(evt.target.id());
    });
    cy.on("tap", (evt: { target: unknown }) => {
      if (evt.target === cy) setSelectedId(null);
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graph.data, relationFilter]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().unselect();
    if (selectedId) {
      const node = cy.getElementById(selectedId);
      if (node.nonempty()) {
        node.select();
        cy.animate({ center: { eles: node }, duration: 180 }, { duration: 180 });
      }
    }
  }, [selectedId]);

  return (
    <div>
      <PageIntro
        title="Graph Explorer"
        description="Taxonomy filter, live Cytoscape canvas, and adjacency list from GET /api/graph."
      />
      <div className="grid gap-4 xl:grid-cols-[200px_minmax(0,1fr)_260px]">
        <Card className="h-fit" data-testid="taxonomy-rail">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.14em] text-fuchsia-900/50">
            Taxonomy
          </h2>
          <button
            type="button"
            className={`mt-3 block w-full rounded-md px-2 py-1.5 text-left text-sm ${
              category === ""
                ? "bg-accent text-white"
                : "hover:bg-fuchsia-50 dark:hover:bg-fuchsia-950/50"
            }`}
            onClick={() => setCategory("")}
          >
            All categories
          </button>
          <ul className="mt-1 max-h-[420px] space-y-0.5 overflow-auto">
            {taxonomy.map(([cat, count]) => (
              <li key={cat}>
                <button
                  type="button"
                  className={`flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm ${
                    category === cat
                      ? "bg-accent text-white"
                      : "hover:bg-fuchsia-50 dark:hover:bg-fuchsia-950/50"
                  }`}
                  onClick={() => setCategory(cat)}
                >
                  <span className="truncate">{cat}</span>
                  <span className="font-mono text-[11px] opacity-70">{count}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        <div className="min-w-0 space-y-3">
          <Card>
            <div className="flex flex-wrap gap-3">
              <label className="min-w-[180px] flex-1 text-sm">
                <span className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Search</span>
                <input
                  className="mt-1 w-full rounded-md border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="skill or role"
                />
              </label>
              <label className="text-sm">
                <span className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Relation</span>
                <select
                  className="mt-1 block rounded-md border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
                  value={relationFilter}
                  onChange={(e) => setRelationFilter(e.target.value)}
                  data-testid="relation-filter"
                >
                  <option value="">All types</option>
                  {(graph.data?.relation_types ?? []).map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {graph.data ? (
              <p className="mt-3 font-mono text-xs text-fuchsia-900/50 dark:text-fuchsia-200/50">
                Graph v{graph.data.graph_version} · {graph.data.node_count} nodes ·{" "}
                {graph.data.edge_count} edges
              </p>
            ) : null}
          </Card>
          {graph.isLoading ? <LoadingState label="Loading graph…" /> : null}
          {graph.isError ? <ErrorState error={graph.error} /> : null}
          <div
            ref={containerRef}
            className="h-[520px] overflow-hidden rounded-lg border border-fuchsia-200/70 bg-[#0c1018] dark:border-fuchsia-900/50"
            data-testid="cytoscape-canvas"
          />
        </div>

        <Card className="h-fit" data-testid="adjacency-panel">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.14em] text-fuchsia-900/50">
            Adjacency
          </h2>
          {selectedNode ? (
            <>
              <p className="mt-3 text-sm font-semibold">{selectedNode.label}</p>
              <p className="font-mono text-xs text-fuchsia-900/50 dark:text-fuchsia-200/50">
                {selectedNode.kind}
                {selectedNode.category ? ` · ${String(selectedNode.category)}` : ""}
              </p>
              {adjacency.length === 0 ? (
                <p className="mt-4 text-sm text-fuchsia-900/50">No neighbors for this filter.</p>
              ) : (
                <ul className="mt-4 max-h-[460px] space-y-2 overflow-auto">
                  {adjacency.map((row) => (
                    <li
                      key={row.id}
                      className="rounded-md border border-fuchsia-100 px-2.5 py-2 dark:border-fuchsia-900/60"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-medium">{row.label}</span>
                        <span className="font-mono text-[10px] uppercase text-fuchsia-900/45">
                          {row.direction}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-[11px] text-fuchsia-900/55 dark:text-fuchsia-200/55">
                        {row.type} · w={row.weight} · {row.kind}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="mt-3 text-sm text-fuchsia-900/55 dark:text-fuchsia-200/55">
              Select a node on the canvas to inspect neighbors by relation type.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
