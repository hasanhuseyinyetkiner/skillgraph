# SkillGraph frontend

React 19 + Vite + TypeScript UI for the SkillGraph demo. Talks to the loopback FastAPI on port **8105** (Vite proxy or `VITE_API_BASE`).

## Prerequisites

- Node 24+ with **pnpm** 12.x (see `packageManager` in `package.json`)
- Backend running at `http://127.0.0.1:8105` (`cd ../backend && uv run python -m app`)

## Commands

```powershell
pnpm install
pnpm dev          # http://127.0.0.1:5105
pnpm lint
pnpm typecheck
pnpm test         # Vitest
pnpm build
pnpm e2e          # Playwright demo arc (API must be up)
pnpm screenshots  # writes ../docs/screenshots/*.png (API must be up)
```

Config: [`.env.example`](.env.example). Leave `VITE_API_BASE` empty to use the Vite `/api` proxy.

## Routes

| Path | Page |
| --- | --- |
| `/` | Dashboard |
| `/skills` | My Skills (demo profile Avery Chen) |
| `/graph` | Graph Explorer (Cytoscape on `GET /api/graph`) |
| `/roles` | Role Explorer (named fit components) |
| `/path` | Path Builder (cycle-safe learning path) |
| `/methodology` | Scoring / eval notes in-app |

## Screenshots

Authentic captures live under [`docs/screenshots/`](../docs/screenshots/). Regenerate with `pnpm screenshots` while API + `pnpm dev` (or Playwright webServer) are available. Do not invent UI mockups.

## Scope reminder

Fit scores shown in Role Explorer / Path Builder are an **exploratory coverage index** — not a hiring probability or employment decision. See [`docs/ALGORITHM.md`](../docs/ALGORITHM.md).
