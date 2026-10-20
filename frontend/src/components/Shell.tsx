import { useQuery } from "@tanstack/react-query";
import { Compass, GitBranch, LayoutDashboard, Moon, Route, Sparkles, Sun, UserRound } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { api } from "../api";
import type { Meta } from "../types";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/skills", label: "My Skills", icon: UserRound },
  { to: "/graph", label: "Graph Explorer", icon: GitBranch },
  { to: "/roles", label: "Role Explorer", icon: Compass },
  { to: "/path", label: "Path Builder", icon: Route },
  { to: "/methodology", label: "Methodology", icon: Sparkles },
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
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_minmax(0,1fr)]">
      <aside className="flex flex-col bg-[#1a0b24] text-fuchsia-50 lg:min-h-screen">
        <div className="px-5 pb-4 pt-6">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-accent text-sm font-bold text-white">S</span>
            <div>
              <p className="text-sm font-semibold tracking-tight">SkillGraph</p>
              <p className="text-xs text-fuchsia-200/60">Exploratory skill ontology</p>
            </div>
          </div>
        </div>
        <nav aria-label="Primary" className="flex gap-1 overflow-x-auto px-3 pb-4 lg:flex-col">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
                  isActive ? "bg-white/10 text-white" : "text-fuchsia-100/70 hover:bg-white/5"
                }`
              }
            >
              <item.icon size={16} aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto px-4 py-4">
          <button
            type="button"
            onClick={toggleTheme}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-sm"
            aria-pressed={dark}
            data-testid="theme-toggle"
          >
            {dark ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
            {dark ? "Light theme" : "Dark theme"}
          </button>
        </div>
      </aside>
      <div className="min-w-0">
        <div
          className="bg-accent px-4 py-2 text-center text-sm font-medium text-white"
          data-testid="demo-banner"
        >
          {meta.data?.banner ?? "Local demo · synthetic data"}
        </div>
        <main id="main" className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
