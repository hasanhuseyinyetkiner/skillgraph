import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import { Card, ErrorState, LoadingState, PageIntro } from "../components/ui";
import type { Meta } from "../types";

export function MethodologyPage() {
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/api/meta") });

  if (meta.isLoading) return <LoadingState label="Loading methodology…" />;
  if (meta.isError) return <ErrorState error={meta.error} />;
  const data = meta.data!;

  return (
    <div>
      <PageIntro
        title="Methodology"
        description="Scoring components, level scale, and disclaimers served by GET /api/meta."
      />
      <Card className="mb-4">
        <p className="text-sm font-semibold">{data.fit_index_label}</p>
        <p className="mt-2 text-sm text-fuchsia-900/70 dark:text-fuchsia-100/70">{data.disclaimer}</p>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-fuchsia-900/50">Method version</dt>
            <dd className="font-medium">{data.method_version}</dd>
          </div>
          <div>
            <dt className="text-fuchsia-900/50">Weights version</dt>
            <dd className="font-medium">{data.weights_version}</dd>
          </div>
          <div>
            <dt className="text-fuchsia-900/50">Semantic</dt>
            <dd className="font-medium">{data.semantic_reason}</dd>
          </div>
          <div>
            <dt className="text-fuchsia-900/50">Embeddings</dt>
            <dd className="font-medium">{data.embeddings_enabled ? "enabled" : "disabled"}</dd>
          </div>
        </dl>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="text-sm font-semibold">Named components</h2>
          <ul className="mt-3 space-y-3">
            {data.component_definitions.map((component) => (
              <li key={component.key} className="rounded-xl bg-fuchsia-50/80 px-3 py-2 dark:bg-fuchsia-950/50">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{component.key.replaceAll("_", " ")}</p>
                  <p className="text-xs text-fuchsia-900/50">
                    {component.in_fit_index ? "in fit index" : "display only"}
                    {component.credit != null ? ` · credit ${component.credit}` : ""}
                  </p>
                </div>
                <p className="mt-1 text-xs text-fuchsia-900/60 dark:text-fuchsia-200/60">{component.summary}</p>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h2 className="text-sm font-semibold">Level scale</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {Object.entries(data.level_scale).map(([key, label]) => (
              <li key={key} className="flex justify-between gap-3">
                <span className="font-medium tabular">{key}</span>
                <span className="text-right text-fuchsia-900/70 dark:text-fuchsia-100/70">{label}</span>
              </li>
            ))}
          </ul>
          <h3 className="mt-5 text-sm font-semibold">Default weights</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {Object.entries(data.weights).map(([key, value]) => (
              <li key={key} className="flex justify-between gap-3">
                <span>{key.replaceAll("_", " ")}</span>
                <span className="tabular font-medium">{value}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
