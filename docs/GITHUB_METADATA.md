# GitHub repository metadata

Use these values in the GitHub repository **About** panel. Do not invent stars, downloads, live-demo URLs, or production claims.

## Description

```
Explainable skill graphs, career transition paths and learning gap analysis with Python and React.
```

(GitHub About description limit: keep under 350 characters; the line above is 98 characters.)

## Topics

```
knowledge-graph
recommendation-system
nlp
networkx
career-development
fastapi
react
machine-learning
cytoscape
portfolio
```

## Homepage

Leave empty unless a public demo URL is deliberately published and kept online.

## Pin rationale

Portfolio piece for explainable skill ontology + deterministic career-path recommendations with measured ranking metrics on synthetic fixtures — including an honest report when graph-augmented scoring ties the overlap baseline on macro P@k / nDCG, while alias resolution still lifts per-role coverage.

## Before tagging a release

- Confirm CI green (`backend`, `frontend`, `compose-smoke`).
- Refresh screenshots with `cd frontend && pnpm screenshots` if UI changed.
- Re-run `GET /api/evaluation` and update README + `docs/EVALUATION.md` with actual numbers — keep macro ties visible.
- Do not claim job-probability, bias-free, or production-ready language.
- License is MIT ([LICENSE](../LICENSE)).
