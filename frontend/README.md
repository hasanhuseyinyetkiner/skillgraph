# SkillGraph frontend

React 19 + Vite + TypeScript UI for the SkillGraph demo. Talks to the loopback FastAPI on port **8105** (Vite proxy or `VITE_API_BASE`).

## Prerequisites

- Node 24+ with **pnpm** 12.x (see `packageManager` in `package.json`)
- For interactive development, run the backend at `http://127.0.0.1:8105` (`cd ../backend && uv run python -m app`).

## Commands

```powershell
pnpm install
pnpm dev          # http://127.0.0.1:5105
pnpm lint
pnpm typecheck
pnpm test         # Vitest
pnpm build
pnpm e2e          # starts isolated API and web servers; ports 8105 and 5105 must be free
pnpm screenshots  # writes ../docs/screenshots/*.png; starts or reuses the API and web servers
```

Config: [`.env.example`](.env.example). Leave `VITE_API_BASE` empty to use the Vite `/api` proxy.

## Routes

| Path | Page |
| --- | --- |
| `/` | Dashboard |
| `/skills` | My Skills (demo profile Avery Chen) |
| `/graph` | Graph Explorer (taxonomy + Cytoscape + adjacency) |
| `/roles` | Role Explorer (gap matrix + evidence weights) |
| `/path` | Path Builder (cycle-safe learning path) |
| `/methodology` | Scoring / eval notes in-app |

## Screenshots

Authentic captures live under [`docs/screenshots/`](../docs/screenshots/). Regenerate with `pnpm screenshots`; its Playwright configuration starts or reuses the API and frontend. When reusing servers it uses their existing data, not the configuration's separate screenshot database.

## Scope reminder

Fit index is exploratory coverage only — never a hiring probability or person score. Synthetic data.
