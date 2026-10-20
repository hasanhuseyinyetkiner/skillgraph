import { useQuery } from "@tanstack/react-query";

import { api } from "../api";
import { Card, ErrorState, LoadingState, PageIntro } from "../components/ui";
import type { Meta, Profile } from "../types";

export function MySkillsPage() {
  const meta = useQuery({ queryKey: ["meta"], queryFn: () => api<Meta>("/api/meta") });
  const profile = useQuery({
    queryKey: ["demo-profile"],
    queryFn: () => api<Profile>("/api/profiles/demo"),
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
      <div className="overflow-x-auto rounded-2xl border border-fuchsia-200/70 bg-white/80 dark:border-fuchsia-900/50 dark:bg-fuchsia-950/30">
        <table className="min-w-full text-left text-sm">
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
