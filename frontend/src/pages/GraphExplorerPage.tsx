import { useQuery } from "@tanstack/react-query";
import cytoscape from "cytoscape";
import { useEffect, useRef, useState } from "react";

import { api } from "../api";
import { Card, ErrorState, LoadingState, PageIntro } from "../components/ui";
import type { GraphPayload } from "../types";

const KIND_COLOR: Record<string, string> = {
  skill: "#C026D3",
  role: "#7C3AED",
  resource: "#DB2777",
};

export function GraphExplorerPage() {
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<ReturnType<typeof cytoscape> | null>(null);

  const graph = useQuery({
    queryKey: ["graph", category, query],
    queryFn: () => {
      const params = new URLSearchParams({ limit: "220" });
      if (category) params.set("category", category);
      if (query.trim()) params.set("q", query.trim());
      return api<GraphPayload>(`/api/graph?${params.toString()}`);
    },
  });

  useEffect(() => {
    if (!graph.data || !containerRef.current) return;

    const elements = [
      ...graph.data.nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          kind: node.kind,
        },
      })),
      ...graph.data.edges.map((edge) => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.type,
        },
      })),
    ];

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            color: "#fff",
            "background-color": (ele: { data: (k: string) => string }) =>
              KIND_COLOR[ele.data("kind")] ?? "#9333EA",
            "font-size": 9,
            "text-valign": "center",
            "text-halign": "center",
            width: 28,
            height: 28,
            "text-wrap": "wrap",
            "text-max-width": 70,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#c4b5fd",
            "target-arrow-color": "#c4b5fd",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 7,
            color: "#a78bfa",
          },
        },
      ],
      layout: { name: "cose", animate: false, padding: 24 },
    });

    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [graph.data]);

  return (
    <div>
      <PageIntro
        title="Graph Explorer"
        description="Interactive cytoscape view of GET /api/graph. Filters call the real API."
      />
      <Card className="mb-4">
        <div className="flex flex-wrap gap-3">
          <label className="text-sm">
            <span className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Category</span>
            <select
              className="ml-2 rounded-xl border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">All</option>
              {(graph.data?.categories ?? []).map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label className="min-w-[220px] flex-1 text-sm">
            <span className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Search</span>
            <input
              className="ml-2 w-[calc(100%-4rem)] rounded-xl border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="skill or role"
            />
          </label>
        </div>
        {graph.data ? (
          <p className="mt-3 text-xs text-fuchsia-900/50 dark:text-fuchsia-200/50">
            Graph v{graph.data.graph_version} · {graph.data.node_count} nodes · {graph.data.edge_count} edges
          </p>
        ) : null}
      </Card>
      {graph.isLoading ? <LoadingState label="Loading graph…" /> : null}
      {graph.isError ? <ErrorState error={graph.error} /> : null}
      <div
        ref={containerRef}
        className="h-[520px] overflow-hidden rounded-2xl border border-fuchsia-200/70 bg-[#14081c] dark:border-fuchsia-900/50"
        data-testid="cytoscape-canvas"
      />
    </div>
  );
}
