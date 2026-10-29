# SkillGraph

SkillGraph is a local prototype for exploring a synthetic skills graph, comparing a profile with role requirements, and expanding learning prerequisites. The React interface visualizes the graph; a FastAPI service scores matches and explains gaps. SQLite stores the demo data, and NetworkX provides the graph snapshot.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/graph-explorer-dark.png">
  <img src="docs/screenshots/graph-explorer-light.png" alt="Graph explorer with the synthetic skills ontology" width="100%">
</picture>

[Watch the graph → role fit → learning path workflow](docs/assets/demo.gif).

An exact skill or validated alias can satisfy a mandatory requirement at the required level. Related skills receive partial credit but do not satisfy that gate. Prerequisite cycles are reported rather than given a false learning order. See [the scoring and path rules](docs/ALGORITHM.md).

The demo uses synthetic profiles and a synthetic ontology. Its [ten-fixture evaluation](docs/EVALUATION.md) compares rankings against hand-assigned judgments, but the fixtures and ontology are project-created, so the results are exploratory rather than independent evidence of recommendation quality. [ESCO research](docs/ESCO.md) describes a possible external data source and the current access limitation. The fit index is not a hiring probability or employment decision.

## Run locally

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js and pnpm. Start the API from the repository root:

```powershell
cd backend
uv sync
uv run python -m app
```

In a second terminal:

```powershell
cd frontend
pnpm install
pnpm dev
```

Open [the app](http://127.0.0.1:5105) or [API documentation](http://127.0.0.1:8105/docs). Try the synthetic Avery Chen profile in Graph Explorer, Role Explorer and Path Builder. Configuration is in [`.env.example`](.env.example) and [`frontend/.env.example`](frontend/.env.example).

## Verify

```powershell
cd backend
uv run ruff check .
uv run pytest -q
cd ../frontend
pnpm lint
pnpm test
pnpm build
pnpm exec playwright install chromium  # once
pnpm e2e
```

Stop the local API and frontend before Playwright; its configuration starts an isolated stack on the same ports. [CI](.github/workflows/ci.yml) also defines link and Compose checks.

This single-user prototype has no multi-user authentication. Use synthetic profiles only; see [security](SECURITY.md), the [evaluation](docs/EVALUATION.md), [performance measurements](docs/PERFORMANCE_BASELINE.md), and [changelog](CHANGELOG.md). Code is available under the [MIT license](LICENSE).
