import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import App from "./App";

vi.stubGlobal(
  "fetch",
  vi.fn(async (input: RequestInfo) => {
    const url = String(input);
    if (url.includes("/api/meta")) {
      return Response.json({
        service: "skillgraph",
        app_env: "demo",
        banner: "Local demo · synthetic data",
        embeddings_enabled: false,
        semantic_reason: "disabled",
        method_version: "skg-baseline-1.0.0",
        weights_version: "weights-1.0.0",
        weights: {},
        level_scale: {},
        component_definitions: [],
        fit_index_label: "Exploratory fit index",
        disclaimer: "Not a job probability.",
        api_port: 8105,
      });
    }
    if (url.includes("/api/profiles/demo")) {
      return Response.json({
        id: 1,
        slug: "demo",
        display_name: "Demo Profile",
        summary: "Synthetic",
        synthetic: true,
        consent_metadata: null,
        skills: [],
      });
    }
    if (url.includes("/summary")) {
      return Response.json({
        profile: {
          id: 1,
          slug: "demo",
          display_name: "Demo Profile",
          summary: "Synthetic",
          synthetic: true,
          consent_metadata: null,
          skills: [],
        },
        skill_count: 0,
        fit_index_label: "Exploratory fit index",
        disclaimer: "Not a job probability.",
        ontology: { skill_count: 0, role_count: 0, resource_count: 0, graph_version: 1 },
        role_fits: [],
      });
    }
    return Response.json({});
  }),
);

describe("App smoke", () => {
  it("renders shell navigation and demo banner", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByTestId("demo-banner")).toHaveTextContent("Local demo · synthetic data");
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Demo Profile" })).toBeInTheDocument();
  });
});
