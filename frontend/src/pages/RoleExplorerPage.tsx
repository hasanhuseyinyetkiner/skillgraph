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
import {
  Button,
  Card,
  ErrorState,
  EvidenceWeightBreakdown,
  LoadingState,
  PageIntro,
} from "../components/ui";
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

const STATUS_TONE: Record<string, string> = {
  satisfied: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  missing: "bg-rose-100 text-rose-900 dark:bg-rose-950 dark:text-rose-200",
  level_gap: "bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-100",
  unconfirmed: "bg-sky-100 text-sky-950 dark:bg-sky-950 dark:text-sky-100",
  not_applicable: "bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300",
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
    return Object.entries(recommend.data.match_type_counts).map(([name, value]) => ({
      name,
      value,
    }));
  }, [recommend.data]);

  const maxCredit = useMemo(() => {
    if (!recommend.data) return 1;
    return Math.max(0.001, ...recommend.data.requirements.map((r) => Number(r.credit ?? 0)));
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
        description="Person-to-role gap matrix and evidence weights for the demo profile. Fit is exploratory coverage — not a hire probability."
      />
      <Card className="mb-4">
        <label className="block text-sm">
          <span className="text-fuchsia-900/50 dark:text-fuchsia-200/50">Role</span>
          <select
            data-testid="role-select"
            className="mt-1 w-full rounded-md border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
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
          <p className="mt-3 text-sm text-fuchsia-900/70 dark:text-fuchsia-100/70">
            {selected.summary || "No summary."}
          </p>
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
        <div className="mb-4 space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <p className="font-mono text-[11px] uppercase tracking-wide text-fuchsia-900/50">
                {recommend.data.fit_index_label}
              </p>
              <p className="mt-2 text-4xl font-semibold tabular" data-testid="fit-index">
                {recommend.data.fit_index.toFixed(1)}
              </p>
              <p className="mt-2 text-sm text-fuchsia-900/60 dark:text-fuchsia-200/60">
                {recommend.data.disclaimer}
              </p>
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
                  <dd className="tabular font-medium">
                    {(recommend.data.coverage * 100).toFixed(1)}%
                  </dd>
                </div>
              </dl>
              {(recommend.data.missing_mandatories?.length ?? 0) > 0 ? (
                <div className="mt-4" data-testid="missing-mandatories">
                  <p className="text-xs font-medium text-fuchsia-900/60 dark:text-fuchsia-200/60">
                    Missing mandatory gates
                  </p>
                  <ul className="mt-1 list-inside list-disc text-sm">
                    {recommend.data.missing_mandatories!.map((row) => (
                      <li key={row.skill_id}>
                        {row.skill_name}{" "}
                        <span className="font-mono text-xs text-fuchsia-900/50">
                          ({row.mandatory_status} · {row.match_type})
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </Card>
            <EvidenceWeightBreakdown
              label="Evidence weight breakdown"
              components={recommend.data.components}
              definitions={meta.data?.component_definitions}
            />
          </div>

          <Card data-testid="gap-matrix">
            <h2 className="text-sm font-semibold">Role ↔ person gap matrix</h2>
            <p className="mt-1 text-xs text-fuchsia-900/50">
              Each row is a role requirement vs the demo profile level, match type, and credit weight.
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-fuchsia-100 font-mono text-[11px] uppercase tracking-wide text-fuchsia-900/50 dark:border-fuchsia-900">
                  <tr>
                    <th className="px-2 py-2 font-medium">Requirement</th>
                    <th className="px-2 py-2 font-medium">Person</th>
                    <th className="px-2 py-2 font-medium">Target</th>
                    <th className="px-2 py-2 font-medium">Match</th>
                    <th className="px-2 py-2 font-medium">Gate</th>
                    <th className="px-2 py-2 font-medium">Credit</th>
                  </tr>
                </thead>
                <tbody data-testid="requirement-rows">
                  {recommend.data.requirements.map((row) => {
                    const credit = Number(row.credit ?? 0);
                    const width = `${Math.min(100, (credit / maxCredit) * 100)}%`;
                    const tone =
                      STATUS_TONE[row.mandatory_status] ??
                      "bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300";
                    return (
                      <tr
                        key={row.skill_id}
                        className="border-b border-fuchsia-50 dark:border-fuchsia-950/80"
                      >
                        <td className="px-2 py-2.5">
                          <span className="font-medium">{row.skill_name}</span>
                          {row.mandatory ? (
                            <span className="ml-1 font-mono text-[10px] text-accent">req</span>
                          ) : null}
                        </td>
                        <td className="px-2 py-2.5 tabular">
                          {row.profile_level == null ? "—" : String(row.profile_level)}
                        </td>
                        <td className="px-2 py-2.5 tabular">{String(row.target_level ?? "—")}</td>
                        <td className="px-2 py-2.5 font-mono text-xs">{row.match_type}</td>
                        <td className="px-2 py-2.5">
                          <span className={`rounded px-1.5 py-0.5 text-xs ${tone}`}>
                            {row.mandatory_status}
                          </span>
                        </td>
                        <td className="px-2 py-2.5 min-w-[120px]">
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 flex-1 overflow-hidden rounded-sm bg-fuchsia-100 dark:bg-fuchsia-950">
                              <div className="h-full rounded-sm bg-accent" style={{ width }} />
                            </div>
                            <span className="font-mono text-xs tabular">{credit.toFixed(2)}</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          {gapChart.length > 0 ? (
            <Card data-testid="gap-chart">
              <h2 className="text-sm font-semibold">Match-type distribution</h2>
              <p className="mt-1 text-xs text-fuchsia-900/50">
                Counts from the scored requirements for this role.
              </p>
              <div className="mt-4 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={gapChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0abfc55" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#C026D3" radius={[4, 4, 0, 0]} />
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
              className="mt-1 w-full rounded-md border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
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
              className="mt-1 w-full rounded-md border border-fuchsia-200 bg-transparent px-3 py-2 dark:border-fuchsia-800"
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
