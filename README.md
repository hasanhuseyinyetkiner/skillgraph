# SkillGraph

Map what you know. Discover where your skills can take you.

Explainable skill graph, role fit breakdown, and cycle-safe learning paths on a synthetic ontology (≥80 skills, ≥20 roles). Embeddings optional.

## Verified local run (Windows)

```powershell
# Terminal 1 — API (127.0.0.1:8105)
cd backend
uv sync
uv run python -m app

# Terminal 2 — Web (127.0.0.1:5105)
cd frontend
pnpm install
pnpm build
pnpm preview
# or: pnpm dev  (needs free RAM; preview is lighter)
```

| Service | URL |
| --- | --- |
| Web | http://127.0.0.1:5105 |
| API docs | http://127.0.0.1:8105/docs |

Ontology seeds on startup (`graph_version` starts at 1).

```powershell
cd backend
uv run pytest -q
```

## Status

Backend + frontend MVP runnable. License pending owner decision.
