# Performance baseline

Measured **2026-10-21** on a local Windows host against a freshly seeded **SQLite** temp database (`uv run python scripts/measure_performance.py` from `backend/`, `PYTHONPATH=.`). Embeddings **disabled**. These are wall-clock samples, not a remote SLA or CI guarantee.

## Workload

| Item | Value |
| --- | ---: |
| Skills | 97 |
| Roles | 24 |
| Relations | 103 |
| Gold fixtures (`dataset_version`) | 10 (`gold-fixtures-1.1.0`) |
| Fit / path target | Analytics Engineer vs `data_analyst_demo` skill set |

## Results (milliseconds)

| Operation | n | mean | median | p95 | min | max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `score_profile_against_role` | 50 | 0.148 | 0.129 | 0.275 | 0.108 | 0.446 |
| `build_learning_path` | 50 | 0.282 | 0.155 | 0.962 | 0.122 | 3.813 |
| `evaluate_rankers` (full gold) | 10 | 23.329 | 23.033 | 28.888 | 19.608 | 28.888 |
| `ontology_quality` audit | 20 | 3.718 | 3.522 | 4.770 | 2.521 | 8.279 |
| `recommend` API stack (demo → Analytics Engineer) | 25 | 25.792 | 24.709 | 42.461 | 16.048 | 54.003 |

## Methodology

1. Seed ontology once into an isolated SQLite file (Alembic migrations + `seed_ontology`).
2. Warm no shared HTTP server for domain timers; each sample calls the pure function or service entrypoint.
3. `recommend` uses the real `session_factory` + `GraphCache` path (SQLAlchemy + NetworkX snapshot), not TestClient HTTP overhead.
4. Report mean / median / empirical p95 from the listed sample counts. No trimming of outliers.
5. Re-run the script after ontology or scoring changes; replace this table with new measured numbers — do not invent deltas.

## Limits

- Host-dependent; another machine or Postgres will differ.
- Path p95 includes occasional NetworkX SCC warm-up spikes on small graphs.
- Docker Compose timing is **not** included here (local Docker **BLOCKED** on the measurement host).
