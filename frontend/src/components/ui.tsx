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
      {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">{eyebrow}</p> : null}
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
      {description ? <p className="max-w-2xl text-sm text-fuchsia-950/60 dark:text-fuchsia-100/60">{description}</p> : null}
    </header>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-2xl border border-fuchsia-200/70 bg-white/80 p-4 shadow-sm backdrop-blur dark:border-fuchsia-900/50 dark:bg-fuchsia-950/30 ${className}`}
    >
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-fuchsia-900/50 dark:text-fuchsia-200/50">{label}</p>
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
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition ${styles} ${className}`}
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

export function ScoreBreakdown({
  components,
  definitions,
  label,
}: {
  components: Record<string, { contribution?: number; value?: number | null; in_fit_index?: boolean; note?: string; reason?: string }>;
  definitions?: Array<{ key: string; summary: string }>;
  label: string;
}) {
  const defMap = new Map((definitions ?? []).map((d) => [d.key, d.summary]));
  return (
    <Card>
      <h2 className="text-sm font-semibold">{label}</h2>
      <p className="mt-1 text-xs text-fuchsia-900/50 dark:text-fuchsia-200/50">
        Named scoring components only — never a job probability.
      </p>
      <ul className="mt-3 space-y-3">
        {Object.entries(components).map(([key, component]) => (
          <li key={key} className="rounded-xl bg-fuchsia-50/80 px-3 py-2 dark:bg-fuchsia-950/50">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium">{key.replaceAll("_", " ")}</p>
              <p className="tabular text-sm font-semibold">
                {component.contribution != null
                  ? component.contribution.toFixed(3)
                  : component.value != null
                    ? Number(component.value).toFixed(3)
                    : "—"}
              </p>
            </div>
            <p className="mt-1 text-xs text-fuchsia-900/60 dark:text-fuchsia-200/60">
              {defMap.get(key) ?? component.note ?? component.reason ?? (component.in_fit_index ? "In fit index" : "Display only")}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
