import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import { Card, ErrorState, LoadingState, PageIntro, Stat } from "../components/ui";
import type { Meta, Profile, ProfileSummary } from "../types";

export function DashboardPage() {
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/api/meta") });
  const profile = useQuery({
    queryKey: ["demo-profile"],
    queryFn: () => api<Profile>("/api/profiles/demo"),
  });
  const summary = useQuery({
    queryKey: ["profile-summary", profile.data?.id],
    queryFn: () => api<ProfileSummary>(`/api/profiles/${profile.data!.id}/summary`),
    enabled: Boolean(profile.data?.id),
  });

  if (profile.isLoading || meta.isLoading) return <LoadingState label="Loading dashboard…" />;
  if (profile.isError) return <ErrorState error={profile.error} />;
  if (meta.isError) return <ErrorState error={meta.error} />;

  const fits = summary.data?.role_fits.slice(0, 5) ?? [];

  return (
    <div>
      <PageIntro
        eyebrow="Demo profile"
        title={profile.data!.display_name}
        description={profile.data!.summary || meta.data!.disclaimer}
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Skills on profile" value={profile.data!.skills.length} />
        <Stat label="Ontology skills" value={summary.data?.ontology.skill_count ?? "—"} />
        <Stat label="Roles" value={summary.data?.ontology.role_count ?? "—"} />
        <Stat label="Graph version" value={summary.data?.ontology.graph_version ?? "—"} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="text-sm font-semibold">{summary.data?.fit_index_label ?? meta.data!.fit_index_label}</h2>
          <p className="mt-2 text-xs text-fuchsia-900/60 dark:text-fuchsia-200/60">
            {summary.data?.disclaimer ?? meta.data!.disclaimer}
          </p>
          {summary.isLoading ? (
            <p className="mt-4 text-sm text-fuchsia-900/50">Computing role fits…</p>
          ) : summary.isError ? (
            <ErrorState error={summary.error} />
          ) : (
            <ul className="mt-4 divide-y divide-fuchsia-100 dark:divide-fuchsia-900/60">
              {fits.map((fit) => (
                <li key={fit.role_id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                  <div>
                    <p className="font-medium">{fit.title}</p>
                    <p className="text-xs text-fuchsia-900/50 dark:text-fuchsia-200/50">{fit.family}</p>
                  </div>
                  <div className="text-right">
                    <p className="tabular font-semibold">{fit.fit_index.toFixed(1)}</p>
                    <p className="text-xs text-fuchsia-900/50">
                      {fit.mandatory_satisfied ? "mandatory ok" : `${fit.mandatory_gap_count} gap(s)`}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <h2 className="text-sm font-semibold">Method snapshot</h2>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Method</dt>
              <dd className="font-medium">{meta.data!.method_version}</dd>
            </div>
            <div>
              <dt className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Weights</dt>
              <dd className="font-medium">{meta.data!.weights_version}</dd>
            </div>
            <div>
              <dt className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Embeddings</dt>
              <dd className="font-medium">{meta.data!.embeddings_enabled ? "enabled" : "off"}</dd>
            </div>
            <div>
              <dt className="text-fuchsia-900/50 dark:text-fuchsia-200/50">App env</dt>
              <dd className="font-medium">{meta.data!.app_env}</dd>
            </div>
          </dl>
        </Card>
      </div>
    </div>
  );
}
