import { useQuery } from "@tanstack/react-query";
import { Compass, GitBranch, LayoutDashboard, Moon, Route, Sparkles, Sun, UserRound } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { api } from "../api";
import type { Meta } from "../types";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/skills", label: "My Skills", icon: UserRound },
  { to: "/graph", label: "Graph", icon: GitBranch },
  { to: "/roles", label: "Roles", icon: Compass },
  { to: "/path", label: "Paths", icon: Route },
  { to: "/methodology", label: "Method", icon: Sparkles },
];

export function Shell() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  const meta = useQuery({
    queryKey: ["meta"],
    queryFn: () => api<Meta>("/api/meta"),
  });

  function toggleTheme() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("skillgraph-theme", next ? "dark" : "light");
    setDark(next);
  }

  return (
    <div className="min-h-screen">
      <div
        className="bg-accent px-4 py-1.5 text-center text-xs font-medium tracking-wide text-white"
        data-testid="demo-banner"
      >
        {meta.data?.banner ?? "Local demo · synthetic data"}
      </div>
      <header className="border-b border-fuchsia-200/60 bg-white/70 backdrop-blur dark:border-fuchsia-900/40 dark:bg-[#14081c]/80">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
          <div className="mr-2 flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-md bg-accent font-mono text-xs font-bold text-white">
              SG
            </span>
            <div>
              <p className="text-sm font-semibold tracking-tight">SkillGraph</p>
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-fuchsia-700/60 dark:text-fuchsia-300/50">
                ontology · fit · paths
              </p>
            </div>
          </div>
          <nav aria-label="Primary" className="flex min-w-0 flex-1 gap-1 overflow-x-auto">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `inline-flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm ${
                    isActive
                      ? "bg-fuchsia-100 text-fuchsia-950 dark:bg-fuchsia-950 dark:text-fuchsia-50"
                      : "text-fuchsia-900/65 hover:bg-fuchsia-50 dark:text-fuchsia-100/65 dark:hover:bg-fuchsia-950/60"
                  }`
                }
              >
                <item.icon size={14} aria-hidden="true" />
                {item.label}
              </NavLink>
            ))}
          </nav>
          <button
            type="button"
            onClick={toggleTheme}
            className="inline-flex items-center gap-1.5 rounded-md border border-fuchsia-200 px-2.5 py-1.5 text-xs dark:border-fuchsia-800"
            aria-pressed={dark}
            data-testid="theme-toggle"
          >
            {dark ? <Sun size={14} aria-hidden="true" /> : <Moon size={14} aria-hidden="true" />}
            {dark ? "Light" : "Dark"}
          </button>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
