# Design review amendments (binding)

These amendments come from the pre-implementation design review (2026-10-20). They **override** any conflicting text in `docs/PRODUCT_SPEC.md`. IDs refer to review findings.

## Environment and delivery (all products)

- **[C-1] No Docker, no local PostgreSQL.** The dev machine is Windows 11 with `uv` (use Python 3.12: `uv python pin 3.12`), Node 24 and pnpm. Provide a **native dev path that is verified locally** (`uv run ...` backend, `pnpm dev` frontend). Local tests may use SQLite through the same SQLAlchemy models; PostgreSQL-only behavior gets a SQLite-safe fallback or a `@pytest.mark.postgres` marker that runs in CI. Write `compose.yaml` and Dockerfiles, but they are verified **only in CI** by a `compose-smoke` job; the README must say so until that job passes.
- **CI** (GitHub Actions, `ubuntu-latest`): backend Ruff + pytest against a PostgreSQL service container; frontend ESLint + `tsc` + Vitest + build; `compose-smoke` (`docker compose up --build -d`, wait for `/ready`, then `docker compose down -v`).
- **[C-6] Ports:** API `8105`, web `5105`, PostgreSQL host port `5405`.
- **[C-2] Loopback by default.** Uvicorn binds `127.0.0.1`; Compose port mappings use `127.0.0.1:` prefixes. No auth in the MVP, so startup refuses a non-loopback host unless `ALLOW_NETWORK_BIND=true` is set explicitly. `APP_ENV=demo` shows a persistent "Local demo · synthetic data" banner.
- **[C-3] No CPU-heavy work on the event loop.** Embedding and graph computations run via `run_in_threadpool` or a process pool. Add a test proving `/health` stays responsive during a heavy request.
- **[C-4] Licensing and git.** Do **not** add a `LICENSE` file; the README states "License: pending owner decision". Do not create remotes or push. Commit locally in small conventional commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`, `ci:`).
- **[C-5] Embeddings are optional.** sentence-transformers lives in an optional extra; torch is pinned to `https://download.pytorch.org/whl/cpu` through an explicit `[[tool.uv.index]]`. The full test suite passes without any embedding model downloaded.
- **Brand:** accent color `#C026D3` (fuchsia). Light and dark themes.

## Product-specific

- **[SKG-1] Versioned graph.** PostgreSQL holds a monotonic `graph_version` incremented in the same transaction as every ontology/skill/role edit. The in-memory NetworkX graph checks the version on each request and reloads when it changed. Every recommendation response and `RecommendationTrace` records `graph_version` and `method_version`. Test with two app instances against one database: edit through one, query through the other, and assert the new version and edge are reflected.
