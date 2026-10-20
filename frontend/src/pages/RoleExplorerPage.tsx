import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import { Button, Card, ErrorState, LoadingState, PageIntro, ScoreBreakdown } from "../components/ui";
import type { Meta, Profile, Recommendation, Role } from "../types";

export function RoleExplorerPage() {
  const [roleId, setRoleId] = useState<number | null>(null);
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/api/meta") });
  const profile = useQuery({
    queryKey: ["demo-profile"],
    queryFn: () => api<Profile>("/api/profiles/demo"),
  });
  const roles = useQuery({
    queryKey: ["roles"],
    queryFn: () => api<Role[]>("/api/roles"),
  });

  const recommend = useMutation({
    mutationFn: (selectedRoleId: number) =>
      api<Recommendation>("/api/recommendations", {
        method: "POST",
        body: JSON.stringify({
          profile_id: profile.data!.id,
          role_id: selectedRoleId,
        }),
      }),
  });

  if (profile.isLoading || roles.isLoading) return <LoadingState label="Loading roles…" />;
  if (profile.isError) return <ErrorState error={profile.error} />;
  if (roles.isError) return <ErrorState error={roles.error} />;

  const selected = roles.data!.find((role) => role.id === roleId) ?? roles.data![0];

  return (
    <div>
      <PageIntro
        title="Role Explorer"
        description="Score the demo profile against a role. Fit is an exploratory index with named components — not a hire probability."
      />
      <Card className="mb-4">
        <label className="block text-sm">
          <span className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Role</span>
          <select
            className="mt-1 w-full rounded-xl border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
            value={selected?.id ?? ""}
            onChange={(e) => {
              const next = Number(e.target.value);
              setRoleId(next);
              recommend.reset();
            }}
          >
            {roles.data!.map((role) => (
              <option key={role.id} value={role.id}>
                {role.title} · {role.family}
              </option>
            ))}
          </select>
        </label>
        {selected ? (
          <p className="mt-3 text-sm text-fuchsia-900/70 dark:text-fuchsia-100/70">{selected.summary || "No summary."}</p>
        ) : null}
        <Button
          className="mt-4"
          disabled={!selected || recommend.isPending}
          onClick={() => selected && recommend.mutate(selected.id)}
        >
          {recommend.isPending ? "Scoring…" : "Compute role fit"}
        </Button>
        {recommend.isError ? <p className="mt-3 text-sm text-rose-600">{recommend.error.message}</p> : null}
      </Card>

      {recommend.data ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <p className="text-xs uppercase tracking-wide text-fuchsia-900/50">{recommend.data.fit_index_label}</p>
            <p className="mt-2 text-4xl font-semibold tabular">{recommend.data.fit_index.toFixed(1)}</p>
            <p className="mt-2 text-sm text-fuchsia-900/60 dark:text-fuchsia-200/60">{recommend.data.disclaimer}</p>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-fuchsia-900/50">Mandatory</dt>
                <dd className="font-medium">
                  {recommend.data.mandatory_satisfied_count}/{recommend.data.mandatory_total}
                  {recommend.data.mandatory_satisfied ? " satisfied" : " incomplete"}
                </dd>
              </div>
              <div>
                <dt className="text-fuchsia-900/50">Coverage</dt>
                <dd className="tabular font-medium">{(recommend.data.coverage * 100).toFixed(1)}%</dd>
              </div>
            </dl>
            <ul className="mt-4 max-h-56 space-y-1 overflow-auto text-sm">
              {recommend.data.requirements.map((row) => (
                <li key={row.skill_id} className="flex justify-between gap-2">
                  <span>
                    {row.skill_name}
                    {row.mandatory ? " *" : ""}
                  </span>
                  <span className="text-fuchsia-900/60 dark:text-fuchsia-200/60">
                    {row.match_type} · {row.mandatory_status}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
          <ScoreBreakdown
            label="Score breakdown"
            components={recommend.data.components}
            definitions={meta.data?.component_definitions}
          />
        </div>
      ) : null}
    </div>
  );
}
