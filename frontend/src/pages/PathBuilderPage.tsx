import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import { Button, Card, ErrorState, LoadingState, PageIntro } from "../components/ui";
import type { LearningPath, Profile, Role } from "../types";

export function PathBuilderPage() {
  const [roleId, setRoleId] = useState<number | null>(null);
  const profile = useQuery({
    queryKey: ["demo-profile"],
    queryFn: () => api<Profile>("/api/profiles/demo"),
  });
  const roles = useQuery({
    queryKey: ["roles"],
    queryFn: () => api<Role[]>("/api/roles"),
  });

  const path = useMutation({
    mutationFn: (selectedRoleId: number) =>
      api<LearningPath>("/api/learning-paths", {
        method: "POST",
        body: JSON.stringify({
          profile_id: profile.data!.id,
          role_id: selectedRoleId,
        }),
      }),
  });

  if (profile.isLoading || roles.isLoading) return <LoadingState label="Loading path builder…" />;
  if (profile.isError) return <ErrorState error={profile.error} />;
  if (roles.isError) return <ErrorState error={roles.error} />;

  const selected = roles.data!.find((role) => role.id === roleId) ?? roles.data![0];

  return (
    <div>
      <PageIntro
        title="Path Builder"
        description="Build a prerequisite-aware learning path from the demo profile to a target role via the API."
      />
      <Card className="mb-4">
        <label className="block text-sm">
          <span className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Target role</span>
          <select
            className="mt-1 w-full rounded-xl border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
            value={selected?.id ?? ""}
            onChange={(e) => {
              setRoleId(Number(e.target.value));
              path.reset();
            }}
          >
            {roles.data!.map((role) => (
              <option key={role.id} value={role.id}>
                {role.title} · {role.family}
              </option>
            ))}
          </select>
        </label>
        <Button
          className="mt-4"
          disabled={!selected || path.isPending}
          onClick={() => selected && path.mutate(selected.id)}
        >
          {path.isPending ? "Building…" : "Build learning path"}
        </Button>
        {path.isError ? <p className="mt-3 text-sm text-rose-600">{path.error.message}</p> : null}
      </Card>

      {path.data ? (
        <div className="space-y-4">
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-fuchsia-900/50">{path.data.fit_index_label}</p>
                <p className="mt-1 text-2xl font-semibold tabular">{path.data.fit_index.toFixed(1)}</p>
                <p className="mt-2 text-sm text-fuchsia-900/60 dark:text-fuchsia-200/60">{path.data.disclaimer}</p>
              </div>
              <div className="text-sm">
                <p>
                  Cycle-free: <span className="font-medium">{path.data.cycle_free ? "yes" : "no"}</span>
                </p>
                <p className="tabular">
                  Duration sum: {path.data.duration_hours_supplied_sum}h
                  {path.data.resources_missing_duration
                    ? ` · ${path.data.resources_missing_duration} missing`
                    : ""}
                </p>
              </div>
            </div>
            <p className="mt-3 text-sm">{path.data.message}</p>
            <p className="mt-2 text-xs text-fuchsia-900/50 dark:text-fuchsia-200/50">{path.data.duration_note}</p>
          </Card>

          <Card>
            <h2 className="text-sm font-semibold">Ordered steps</h2>
            {path.data.ordered_steps.length === 0 ? (
              <p className="mt-3 text-sm text-fuchsia-900/50">No gap steps returned for this role.</p>
            ) : (
              <ol className="mt-3 space-y-3">
                {path.data.ordered_steps.map((step, index) => (
                  <li
                    key={`${step.skill_id}-${index}`}
                    className="rounded-xl bg-fuchsia-50/80 px-3 py-2 dark:bg-fuchsia-950/50"
                  >
                    <p className="text-sm font-medium">
                      {index + 1}. {String(step.skill_name ?? `Skill ${step.skill_id}`)}
                    </p>
                    {step.reason ? (
                      <p className="mt-1 text-xs text-fuchsia-900/60 dark:text-fuchsia-200/60">{String(step.reason)}</p>
                    ) : null}
                    {Array.isArray(step.resources) && step.resources.length > 0 ? (
                      <ul className="mt-2 space-y-1 text-xs text-fuchsia-900/70 dark:text-fuchsia-100/70">
                        {step.resources.map((resource) => (
                          <li key={String(resource.id)}>
                            {String(resource.title)}
                            {resource.duration_hours != null ? ` · ${String(resource.duration_hours)}h` : ""}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>
      ) : null}
    </div>
  );
}
