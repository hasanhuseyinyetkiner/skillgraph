# Release readiness

Checklist for a local / portfolio release of SkillGraph. This is **not** a production go-live guide. License is pending; do not publish SPDX claims until the owner adds a `LICENSE` file.

## Must be true before tagging

| Check | How |
| --- | --- |
| CI green | GitHub Actions: backend (Ruff + pytest + Postgres), frontend (lint / tsc / vitest / build), `compose-smoke` |
| Native demo boots | `uv run python -m app` on `8105` + `pnpm dev` on `5105`; `/ready` OK |
| Eval honesty | `GET /api/evaluation` macros match README + [EVALUATION.md](EVALUATION.md); **do not** claim graph beats overlap when macros tie |
| Screenshots authentic | `cd frontend && pnpm screenshots` if UI changed; Graph / Role / Path × light+dark in `docs/screenshots/` |
| Scope language | Fit index = exploratory; never hiring probability / person worth / auto decisions |
| Secrets | No `.env`, credentials, or real HR data committed |
| Loopback | Default bind `127.0.0.1`; `ALLOW_NETWORK_BIND` only when intentional |
| Docs links | README + `docs/*` local links resolve; About text from [GITHUB_METADATA.md](GITHUB_METADATA.md) |

## Should verify

- [ ] Seed counts documented in README still match `GET /api/ontology/quality` (skills / roles / resources / relations)
- [ ] Playwright `pnpm e2e` demo arc: profile → graph → role fit → learning path
- [ ] Backend `uv run pytest -q` and `uv run ruff check .`
- [ ] Frontend `pnpm lint && pnpm test && pnpm build`
- [ ] Cycle demos: Path Builder cycle-free path + ontology quality lists known seed cycles
- [ ] Privacy: export / erase / demo reset still work

## Explicit non-goals for this MVP

- Public live-demo URL or multi-tenant auth
- Embedding model download required for demo
- Claiming external taxonomy compliance (O\*NET, ESCO, …) without verified attribution
- Rewriting git history, force-push, or inventing LICENSE text
- Manipulating or hiding equal aggregate eval metrics

## Suggested tag note template

```
SkillGraph MVP demo — explainable skill graph + deterministic fit + cycle-safe paths.
Eval: macro P@k/nDCG tie between overlap and graph (documented); coverage deltas on aliases.
Synthetic data only. License pending.
```

After tagging: update GitHub About from [GITHUB_METADATA.md](GITHUB_METADATA.md). Push only with owner authorization.
