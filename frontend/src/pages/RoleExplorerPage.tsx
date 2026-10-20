import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api } from "../api";
import { Button, Card, ErrorState, LoadingState, PageIntro, ScoreBreakdown } from "../components/ui";
import type { Meta, Profile, Recommendation, Role } from "../types";

type CompareResult = {
  shared_identity_skills: string[];
  only_a_mandatory_gaps: string[];
  only_b_mandatory_gaps: string[];
  role_a: Recommendation;
  role_b: Recommendation;
  graph_version: number;
  method_version: string;
};

export function RoleExplorerPage() {
  const [roleId, setRoleId] = useState<number | null>(null);
  const [compareBId, setCompareBId] = useState<number | null>(null);
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

  const compare = useMutation({
    mutationFn: ({ a, b }: { a: number; b: number }) =>
      api<CompareResult>("/api/recommendations/compare", {
        method: "POST",
        body: JSON.stringify({
          profile_id: profile.data!.id,
          role_a_id: a,
          role_b_id: b,
        }),
      }),
  });

  const gapChart = useMemo(() => {
    if (!recommend.data) return [];
    const counts = recommend.data.match_type_counts;
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [recommend.data]);

  if (profile.isLoading || roles.isLoading) return <LoadingState label="Loading roles…" />;
  if (profile.isError) return <ErrorState error={profile.error} />;
  if (roles.isError) return <ErrorState error={roles.error} />;

  const selected = roles.data!.find((role) => role.id === roleId) ?? roles.data![0];
  const compareB =
    roles.data!.find((role) => role.id === compareBId) ??
    roles.data!.find((role) => role.title === "Analytics Engineer") ??
    roles.data![1];

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
            data-testid="role-select"
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
          data-testid="compute-fit"
          disabled={!selected || recommend.isPending}
          onClick={() => selected && recommend.mutate(selected.id)}
        >
          {recommend.isPending ? "Scoring…" : "Compute role fit"}
        </Button>
        {recommend.isError ? <p className="mt-3 text-sm text-rose-600">{recommend.error.message}</p> : null}
      </Card>

      {recommend.data ? (
        <div className="mb-4 grid gap-4 lg:grid-cols-2">
          <Card>
            <p className="text-xs uppercase tracking-wide text-fuchsia-900/50">{recommend.data.fit_index_label}</p>
            <p className="mt-2 text-4xl font-semibold tabular" data-testid="fit-index">
              {recommend.data.fit_index.toFixed(1)}
            </p>
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
            <ul className="mt-4 max-h-56 space-y-1 overflow-auto text-sm" data-testid="requirement-rows">
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
          {gapChart.length > 0 ? (
            <Card className="lg:col-span-2" data-testid="gap-chart">
              <h2 className="text-sm font-semibold">Match-type distribution</h2>
              <p className="mt-1 text-xs text-fuchsia-900/50">Counts from the scored requirements for this role.</p>
              <div className="mt-4 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={gapChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0abfc55" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#C026D3" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}

      <Card>
        <h2 className="text-sm font-semibold">Compare two roles</h2>
        <p className="mt-1 text-xs text-fuchsia-900/60 dark:text-fuchsia-200/60">
          Shared identity skills and mandatory gaps unique to each target.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="text-fuchsia-900/50">Role A</span>
            <select
              data-testid="compare-a"
              className="mt-1 w-full rounded-xl border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
              value={selected?.id ?? ""}
              onChange={(e) => setRoleId(Number(e.target.value))}
            >
              {roles.data!.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.title}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-fuchsia-900/50">Role B</span>
            <select
              data-testid="compare-b"
              className="mt-1 w-full rounded-xl border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
              value={compareB?.id ?? ""}
              onChange={(e) => setCompareBId(Number(e.target.value))}
            >
              {roles.data!.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.title}
                </option>
              ))}
            </select>
          </label>
        </div>
        <Button
          className="mt-4"
          data-testid="compare-roles"
          disabled={!selected || !compareB || compare.isPending || selected.id === compareB.id}
          onClick={() => selected && compareB && compare.mutate({ a: selected.id, b: compareB.id })}
        >
          {compare.isPending ? "Comparing…" : "Compare roles"}
        </Button>
        {compare.isError ? <p className="mt-3 text-sm text-rose-600">{compare.error.message}</p> : null}
        {compare.data ? (
          <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3" data-testid="compare-result">
            <div>
              <p className="font-medium">Shared identity</p>
              <p className="mt-1 text-fuchsia-900/70 dark:text-fuchsia-100/70">
                {compare.data.shared_identity_skills.join(", ") || "None"}
              </p>
            </div>
            <div>
              <p className="font-medium">Only A gaps</p>
              <p className="mt-1 text-fuchsia-900/70 dark:text-fuchsia-100/70">
                {compare.data.only_a_mandatory_gaps.join(", ") || "None"}
              </p>
            </div>
            <div>
              <p className="font-medium">Only B gaps</p>
              <p className="mt-1 text-fuchsia-900/70 dark:text-fuchsia-100/70">
                {compare.data.only_b_mandatory_gaps.join(", ") || "None"}
              </p>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
