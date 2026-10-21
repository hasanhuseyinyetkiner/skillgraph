import type { ReactNode } from "react";

export function PageIntro({
  eyebrow,
  title,
  description,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
}) {
  return (
    <header className="mb-6 space-y-1">
      {eyebrow ? (
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-accent">{eyebrow}</p>
      ) : null}
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
      {description ? (
        <p className="max-w-2xl text-sm text-fuchsia-950/60 dark:text-fuchsia-100/60">{description}</p>
      ) : null}
    </header>
  );
}

export function Card({
  children,
  className = "",
  ...props
}: React.HTMLAttributes<HTMLElement> & { children: ReactNode }) {
  return (
    <section
      className={`rounded-lg border border-fuchsia-200/70 bg-white/85 p-4 dark:border-fuchsia-900/50 dark:bg-[#160a1f]/70 ${className}`}
      {...props}
    >
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card>
      <p className="font-mono text-[11px] uppercase tracking-wide text-fuchsia-900/50 dark:text-fuchsia-200/50">
        {label}
      </p>
      <p className="mt-2 text-3xl font-semibold tabular tracking-tight">{value}</p>
      {hint ? <p className="mt-1 text-xs text-fuchsia-900/50 dark:text-fuchsia-200/50">{hint}</p> : null}
    </Card>
  );
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }) {
  const styles =
    variant === "primary"
      ? "bg-accent text-white hover:brightness-110 disabled:opacity-50"
      : "border border-fuchsia-300 bg-transparent hover:bg-fuchsia-50 dark:border-fuchsia-800 dark:hover:bg-fuchsia-950";
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium transition ${styles} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function ErrorState({ error }: { error: Error }) {
  return (
    <Card className="border-rose-300 bg-rose-50 text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
      <p className="font-medium">Could not load data</p>
      <p className="mt-1 text-sm">{error.message}</p>
    </Card>
  );
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <Card className="animate-pulse text-sm text-fuchsia-900/50">{label}</Card>;
}

export function EvidenceWeightBreakdown({
  components,
  definitions,
  label,
}: {
  components: Record<
    string,
    { contribution?: number; value?: number | null; in_fit_index?: boolean; note?: string; reason?: string }
  >;
  definitions?: Array<{ key: string; summary: string }>;
  label: string;
}) {
  const defMap = new Map((definitions ?? []).map((d) => [d.key, d.summary]));
  const entries = Object.entries(components);
  const maxAbs = Math.max(
    0.001,
    ...entries.map(([, c]) => Math.abs(Number(c.contribution ?? c.value ?? 0))),
  );

  return (
    <Card data-testid="evidence-weights">
      <h2 className="text-sm font-semibold">{label}</h2>
      <p className="mt-1 text-xs text-fuchsia-900/50 dark:text-fuchsia-200/50">
        Contribution to the fit index (or display-only signals). Not a job probability.
      </p>
      <ul className="mt-4 space-y-3">
        {entries.map(([key, component]) => {
          const raw = Number(component.contribution ?? component.value ?? 0);
          const width = `${Math.min(100, (Math.abs(raw) / maxAbs) * 100)}%`;
          return (
            <li key={key}>
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-sm font-medium">{key.replaceAll("_", " ")}</p>
                <p className="font-mono text-sm tabular font-semibold">
                  {component.contribution != null
                    ? component.contribution.toFixed(3)
                    : component.value != null
                      ? Number(component.value).toFixed(3)
                      : "—"}
                </p>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-sm bg-fuchsia-100 dark:bg-fuchsia-950">
                <div
                  className={`h-full rounded-sm ${component.in_fit_index === false ? "bg-fuchsia-300/70 dark:bg-fuchsia-700/50" : "bg-accent"}`}
                  style={{ width }}
                />
              </div>
              <p className="mt-1 text-xs text-fuchsia-900/60 dark:text-fuchsia-200/60">
                {defMap.get(key) ??
                  component.note ??
                  component.reason ??
                  (component.in_fit_index ? "In fit index" : "Display only")}
              </p>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

export const ScoreBreakdown = EvidenceWeightBreakdown;
