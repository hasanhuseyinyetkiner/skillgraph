import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api";
import { Button, Card, ErrorState, LoadingState, PageIntro } from "../components/ui";
import type { Meta, Profile } from "../types";

export function MySkillsPage() {
  const queryClient = useQueryClient();
  const [exportText, setExportText] = useState<string | null>(null);
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/api/meta") });
  const profile = useQuery({
    queryKey: ["demo-profile"],
    queryFn: () => api<Profile>("/api/profiles/demo"),
  });

  const reset = useMutation({
    mutationFn: () => api<Profile>("/api/profiles/demo/reset", { method: "POST" }),
    onSuccess: (data) => {
      queryClient.setQueryData(["demo-profile"], data);
      void queryClient.invalidateQueries({ queryKey: ["profile-summary"] });
      setExportText(null);
    },
  });

  const exportProfile = useMutation({
    mutationFn: (profileId: number) =>
      api<Record<string, unknown>>(`/api/profiles/${profileId}/export`),
    onSuccess: (payload) => setExportText(JSON.stringify(payload, null, 2)),
  });

  const erase = useMutation({
    mutationFn: async (profileId: number) => {
      await api<void>(`/api/profiles/${profileId}`, { method: "DELETE" });
      return api<Profile>("/api/profiles/demo/reset", { method: "POST" });
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["demo-profile"], data);
      void queryClient.invalidateQueries({ queryKey: ["profile-summary"] });
      setExportText(null);
    },
  });

  if (profile.isLoading) return <LoadingState label="Loading skills…" />;
  if (profile.isError) return <ErrorState error={profile.error} />;

  const levelScale = meta.data?.level_scale ?? {};

  return (
    <div>
      <PageIntro
        title="My Skills"
        description={`Demo profile “${profile.data!.display_name}” with ${profile.data!.skills.length} asserted skills from the API.`}
      />

      <Card className="mb-4">
        <p className="text-sm font-semibold">Privacy controls</p>
        <p className="mt-1 text-xs text-fuchsia-900/60 dark:text-fuchsia-200/60">
          Export, erase, or reset the synthetic demo profile. Erase deletes the current row then reseeds demo.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            data-testid="export-profile"
            disabled={exportProfile.isPending}
            onClick={() => exportProfile.mutate(profile.data!.id)}
          >
            {exportProfile.isPending ? "Exporting…" : "Export JSON"}
          </Button>
          <Button
            variant="ghost"
            data-testid="reset-demo"
            disabled={reset.isPending}
            onClick={() => reset.mutate()}
          >
            {reset.isPending ? "Resetting…" : "Reset demo"}
          </Button>
          <Button
            variant="ghost"
            data-testid="erase-profile"
            disabled={erase.isPending}
            onClick={() => erase.mutate(profile.data!.id)}
          >
            {erase.isPending ? "Erasing…" : "Erase + reseed"}
          </Button>
        </div>
        {exportProfile.isError ? (
          <p className="mt-2 text-sm text-rose-600">{exportProfile.error.message}</p>
        ) : null}
        {reset.isError ? <p className="mt-2 text-sm text-rose-600">{reset.error.message}</p> : null}
        {erase.isError ? <p className="mt-2 text-sm text-rose-600">{erase.error.message}</p> : null}
        {exportText ? (
          <pre
            data-testid="export-json"
            className="mt-3 max-h-48 overflow-auto rounded-xl bg-fuchsia-50/80 p-3 text-xs dark:bg-fuchsia-950/50"
          >
            {exportText}
          </pre>
        ) : null}
      </Card>

      <div className="overflow-x-auto rounded-2xl border border-fuchsia-200/70 bg-white/80 dark:border-fuchsia-900/50 dark:bg-fuchsia-950/30">
        <table className="min-w-full text-left text-sm" data-testid="skills-table">
          <thead className="border-b border-fuchsia-100 text-xs uppercase tracking-wide text-fuchsia-900/50 dark:border-fuchsia-900">
            <tr>
              <th className="px-4 py-3 font-medium">Skill</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium">Level</th>
              <th className="px-4 py-3 font-medium">Asserted label</th>
            </tr>
          </thead>
          <tbody>
            {profile.data!.skills.map((skill) => {
              const levelKey =
                skill.self_assessed_level == null ? "unknown" : String(skill.self_assessed_level);
              return (
                <tr key={skill.skill_id} className="border-b border-fuchsia-50 dark:border-fuchsia-950">
                  <td className="px-4 py-3 font-medium">{skill.canonical_name ?? `Skill ${skill.skill_id}`}</td>
                  <td className="px-4 py-3">{skill.category ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className="tabular font-medium">{levelKey}</span>
                    <span className="ml-2 text-xs text-fuchsia-900/50 dark:text-fuchsia-200/50">
                      {levelScale[levelKey] ?? ""}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-fuchsia-900/70 dark:text-fuchsia-100/70">
                    {skill.asserted_label ?? "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {profile.data!.skills.length === 0 ? (
        <Card className="mt-4 text-sm">Demo profile has no skills yet.</Card>
      ) : null}
    </div>
  );
}
