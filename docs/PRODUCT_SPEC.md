# CURSOR AGENT PROMPT — SKILLGRAPH

You are a senior knowledge-graph engineer, NLP scientist, full-stack product engineer and open-source maintainer. Develop **SkillGraph**, an explainable skill intelligence and internal career mobility tool. Implement a complete functioning product, not disconnected embeddings or mocked recommendation screens. Read `.cursor/rules/*.mdc` where present.

## Product concept

Users create or import a **synthetic/voluntary** skills profile, browse a graph of relationships among skills, occupations and learning resources, and explore realistic possible transitions to other roles. Each suggested path explains which skills already match, which are missing, and what learning steps may help. **No automated promotion, applicant rejection or employee worth scoring.**

**Technical differentiator:** knowledge graph + explicit weighted skill relations + semantic synonym search + explainable recommendation baseline + evaluation against hand-labeled demo fixtures.

## Stack

- Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, NetworkX, sentence-transformers, scikit-learn, pandas, pytest, Ruff.
- React + Vite + TypeScript + Tailwind, Cytoscape.js with React integration or React Flow for interactive graph, TanStack Query, React Router, Recharts for gap analysis, Lucide.
- Docker Compose, GitHub Actions, Vitest + Playwright.
- Keep NetworkX service-based graph storage for MVP, persisting nodes/edges in PostgreSQL. Do not introduce Neo4j unless a concrete requirement makes it worthwhile.

## Data model

Skill(id, canonical_name, aliases, category, source, confidence), SkillRelation(source, target, type, weight, provenance), Role(id, title, family), RoleRequirement(role_id, skill_id, target_level, importance, mandatory), Profile(id, consent_metadata), ProfileSkill(profile_id, skill_id, self_assessed_level, last_verified), LearningResource(id, title, prerequisites, target_skill, duration_estimate, source), RecommendationTrace(input snapshot, method version, score breakdown).

Skills should have a documented level scale (e.g. 0–5) and explicit unknown values; do not treat unlisted skills as definite absence. Seed at least 80 synthetic/clearly attributed skills, 20 roles and 30 learning resources with several career clusters. Include understandable transfer cases, e.g. Data Analyst -> Analytics Engineer, QA Engineer -> Automation Engineer. No fake employment outcome claims.

## Features

1. Skills inventory editor: add/delete/update skills and self-assessed confidence, import a well-formed CSV and preview mapping.
2. Ontology/synonyms: map terms such as `Postgres` and `PostgreSQL`; graph edges for prerequisite, related, broader/narrower skills. Let users inspect provenance and edit uncertain mappings.
3. Graph Explorer: zoom/pan/search/filter by skill family, role and relation type; meaningful tooltip/drawer with evidence.
4. Role Explorer: view mandatory vs nice-to-have requirements, fit components and missing or low-level skills.
5. Explainable recommendations: baseline weighted requirement matching and graph-based relationship scores, with separately displayed semantic similarity signal; configurable weights and justification.
6. Learning path builder: prerequisite-aware, cycle-safe ordering for missing skills, with resource recommendations and honest estimates where supplied; detect/flag cycles.
7. Compare two target roles: missing skills, estimated learning prerequisites, and overlapping transferable skills.
8. Privacy-first profile controls including export, edit, erase and synthetic demo reset.

## Algorithm requirements

- Start with a deterministic, comprehensible baseline independent of embedding availability.
- Normalize aliases before matching. Distinguish exact skill match, validated synonym, related skill and model-suggested semantic similarity.
- Hard mandatory requirements should not be hidden by high overall semantic scores.
- Decompose score into named components with versioned weights; don't present score as a percentage chance of obtaining a job.
- Avoid cycles in prerequisites; if the graph contains one, explain the data issue and don't silently generate an impossible sequence.
- When embeddings are disabled/offline or a model fails to load, baseline search and explanations must continue working.
- Record recommendation metadata so differences after ontology edits can be explained.

## UI

Create a premium dark/light friendly app with Dashboard, My Skills, Graph Explorer, Role Explorer, Path Builder and Methodology pages. Main feature is an attractive, **interactive** graph connected to real API data. Show skill gaps and matched evidence. Accessible tooltips, keyboard navigation where practical, responsive layout, skeleton loading, empty/error states. Real screenshots from app only.

## API

Suggested: `GET/POST /api/skills`, `GET /api/graph`, `GET/POST /api/roles`, `GET/PUT /api/profiles/{id}`, `POST /api/recommendations`, `POST /api/learning-paths`, `GET /api/ontology/quality`, `GET /health`. Keep recommendation algorithm as independently testable Python module.

## Tests and evaluation

- Synthetic gold dataset of role/profile suitability created by explicit business rules and then independently hand-checked; clearly separate that from real user evidence.
- Ranking metrics: Precision@K, Recall@K or nDCG@K using labeled fixtures; compare basic skill-overlap baseline with graph-augmented version. Report actual measurements only.
- Unit tests for alias normalization, mandatory requirement treatment, score weight invariants, graph path finding, cycles, unknown skills, missing prerequisites and empty profile.
- API tests plus Playwright flow: load demo profile -> visualize graph -> select target role -> inspect gap -> create path.
- Test graph query performance on a documented synthetic scale; don't fabricate result numbers.

## Ethics + security

Profiles may include personal data; default sample profiles are synthetic, allow deletion, clearly label recommendations as exploratory, and never apply protected attributes to occupational potential. External taxonomy/education datasets require attribution and license verification. Multi-user deployments require backend access control and tenant isolation.

## README requirements — premium GitHub portfolio quality

English headline: "Map what you know. Discover where your skills can take you." Include authentic graph screenshot near the top, interactive product tour, actual feature grid, sample profile-to-career journey, graph schema Mermaid diagram, deterministic ranking explanation, data model, metrics with real test results, Quick Start tested end to end, API curl example, docs for how to modify ontology, privacy/limitations, contribution guide and selected license. Add `docs/GITHUB_METADATA.md`: description `Explainable skill graphs, career transition paths and learning gap analysis with Python and React.`; topics `knowledge-graph`, `recommendation-system`, `nlp`, `networkx`, `career-development`, `fastapi`, `react`, `machine-learning`.

## Phases / acceptance

Phase 1: core data model + PostgreSQL + seed ontology + working frontend/backend/Docker.
Phase 2: alias normalization, matching baseline, graph explorer and role browser.
Phase 3: graph-aware recommendations, learning path generator, confidence/explanations, evaluation and tests.
Phase 4: UX/accessibility, reproducible demo, real screenshots, CI, in-depth README, docs and clean install.

**Definition of done:** Demo profile loads into live graph, searching a target role produces a traceable suggestion and a cycle-safe learning path, results change meaningfully with edited skills, and unit/e2e tests support the behavior. Document unverified/unfinished parts honestly. Do not push to GitHub or deploy unless explicitly authorized.
