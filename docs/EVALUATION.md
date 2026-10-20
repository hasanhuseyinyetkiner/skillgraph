# Evaluation

Measured on 2026-10-20 against the seeded local demo (`GET /api/evaluation`, `graph_version=3`, `method_version=skg-baseline-1.0.0`, embeddings **disabled**).

## What is being measured

| Item | Policy |
| --- | --- |
| Fixtures | Five hand-labeled synthetic profiles in `app/domain/gold.py` |
| Candidate set | Only roles listed in each fixture’s `labels` map; unlabeled roles excluded |
| Relevance | Fixture grades 3 / 2 / 1 / 0 — business-rule judgments on the ontology, **not** hiring outcomes |
| Relevant for P@k / R@k | grade > 0 |
| **Overlap baseline** | Asserted label must equal the requirement’s **canonical** name after normalize — **no** alias table, **no** related edges, **no** level weighting (`overlap_baseline_score`) |
| **Graph-augmented** | Exact + validated synonym + related/broader/narrower soft credit (`score_profile_against_role`) |
| Rank key | Method score descending, then role title ascending (stable tie-break) |
| Metrics | Macro average of Precision@3/5, Recall@3/5, nDCG@3/5 over the five fixtures |

Grades were assigned from explicit rules (primary role vs stretch vs no transfer) and are **not** copied from the scorer. Fit / coverage scores are exploratory indices — never job-offer probabilities.

## Macro results (actual)

| Method | P@3 | P@5 | R@3 | R@5 | nDCG@3 | nDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Overlap baseline | 1.0000 | 0.9600 | 0.5450 | 0.8583 | 0.9860 | 0.9754 |
| Graph-augmented | 1.0000 | 0.9600 | 0.5450 | 0.8583 | 0.9860 | 0.9754 |

**The graph ranker does not beat the overlap baseline on these macro ranking metrics.** Do not hide or rephrase this as an aggregate win. Top-k *relevance-grade* sequences are identical for every fixture at k=3 and k=5, so precision, recall, and nDCG cannot diverge.

That is not a failure of the product claim. The graph still changes **coverage** and explanations; this eval set is too coarse (small labeled candidate sets, many tied relevance grades) for related-edge credit to reorder grades inside the top-k window.

## Why the macros tie (error / design analysis)

1. **Metrics see grades, not scores.** P@k / R@k / nDCG@k consume the sequence of fixture grades after sorting by method score. If two methods produce the same grade multiset in the top-k window, every metric matches — even when absolute coverage differs a lot.
2. **Many equal grades.** Fixtures pack several roles at grade 2 or 1. Reordering *within* a grade band is invisible to nDCG when the ideal DCG uses the same grade list.
3. **Alias lifts coverage without flipping grades.** On `synonym_specialist`, graph coverage for Backend Engineer jumps (aliases resolve), but the role was already labeled grade 3 and stays at the top for both methods.
4. **Related credit is weak and gated.** Soft credit (0.45 × weight) rarely outranks a stronger identity match enough to swap a grade-3 role with a grade-2 role in this tiny catalog.
5. **Overlap is not “graph minus edges.”** It is a harsher name-equality baseline. Coverage deltas therefore overstate “ranking power” relative to a synonym-aware identity baseline.

## Why nDCG is not 1.0

On `data_analyst_demo`, both rankers place **Senior Data Analyst** (grade 2, high coverage) above **Data Analyst** (grade 3). That grade inversion in the top-3 window is why nDCG@3 ≈ 0.986 rather than 1.0. The scorer optimizes coverage of stated requirements, not the fixture’s career-level preference — an honest mismatch, not a bug to paper over.

## Ranking-order check

For each of the five fixtures, comparing sorted relevance lists:

| Fixture | Top-3 grades | Top-5 grades | Graph vs overlap |
| --- | --- | --- | --- |
| synonym_specialist | `[3,2,2]` | `[3,2,2,1,1]` | Identical |
| data_analyst_demo | `[2,3,2]` | `[2,3,2,1,1]` | Identical |
| qa_manual | `[3,2,1]` | `[3,2,1,1,0]` | Identical |
| automation_ready | `[3,3,2]` | `[3,3,2,1,1]` | Identical |
| cloud_admin | `[3,2,2]` | `[3,2,2,1,1]` | Identical |

### Within-grade ranking changes (metrics unchanged)

Within equal-grade bands, order **can** differ. Example: on `automation_ready`, graph may place Backend Engineer before QA Lead (both grade 1) while overlap reverses them. Same grades → identical P@k / nDCG. Document these as explainability / score-magnitude differences, not ranking wins.

## Per-profile coverage deltas (honest cases)

Coverage here is the graph fit `coverage` (0–1) vs overlap fraction — **not** a claim that ranking improved.

### Where graph coverage helps (aliases / related)

| Fixture | Role | Graph coverage | Overlap coverage | Notes |
| --- | --- | ---: | ---: | --- |
| `synonym_specialist` | Backend Engineer | **0.5457** | 0.1429 | `Postgres` / `js` resolve via alias (`validated_synonym`); overlap requires canonical asserted labels |
| `synonym_specialist` | Full Stack Engineer | 0.5022 | 0.1429 | Same alias lift |
| `data_analyst_demo` | BI Developer | 0.7300 | 0.5714 | Related edges fill some non-mandatory gaps |
| `qa_manual` | QA Engineer | 0.8947 | 0.8000 | Related credit on adjacent QA skills |
| `cloud_admin` | DevOps Engineer | 0.7271 | 0.6667 | Related infrastructure edges |

Despite large coverage gaps on `synonym_specialist`, **top-5 relevance grades stay `[3,2,2,1,1]` for both methods**.

### Where overlap coverage is higher (related noise / dilution)

| Fixture | Role | Graph coverage | Overlap coverage | Notes |
| --- | --- | ---: | ---: | --- |
| `data_analyst_demo` | ML Engineer (grade 0) | 0.2130 | **0.2500** | Related edges do not always dominate; identity-only fraction can score higher on sparse overlap |
| `data_analyst_demo` | Frontend Engineer (0) | 0.1154 | **0.1429** | Same pattern |
| `qa_manual` | Automation Engineer (1) | 0.2121 | **0.2857** | Graph related credit &lt; overlap identity on this stretch role |
| `cloud_admin` | Backend Engineer (1) | 0.3478 | **0.4286** | Overlap higher; still same top-k grade list |
| `cloud_admin` | Data Engineer (1) | 0.1892 | **0.3000** | Overlap higher |

Related edges are intentionally weak and never satisfy mandatory requirements. On stretch roles they can move coverage either way without changing which relevance grades land in the top-k.

## What is *not* proven by this eval

| Claim | Status |
| --- | --- |
| Graph beats overlap on macro P@k / nDCG | **Not shown** — macros tie |
| Alias resolution improves explainability / identity coverage | Supported by per-role coverage (e.g. synonym_specialist) |
| Related edges improve ranking quality | **Unproven** on this set; sometimes lowers coverage vs overlap |
| Fit index predicts hiring / mobility outcomes | **Not evaluated** — synthetic grades only |
| Embeddings improve anything | **Out of scope** — disabled; composite weight 0 |
| Fairness / bias audits | **Not claimed** |

Do not invent improvements. Future work that could separate the methods: larger graded catalogs, graded preference among near-ties, mandatory-gap recovery metrics, or a synonym-aware identity baseline — not fabricated lifts on this fixture set.

## How to reproduce

```powershell
# With API running on 8105:
curl http://127.0.0.1:8105/api/evaluation

# Or via pytest (prints EVAL_METRICS JSON):
cd backend
uv run pytest -q -s tests/test_api.py::test_evaluation_reports_measured_metrics
```

## Small-n and metric sensitivity

| Factor | Effect on this run |
| --- | --- |
| **n = 5 fixtures** | One fixture that swapped a grade-3 with a grade-2 would move macros a lot; absence of such a swap is not strong evidence of ranking parity in the wild. |
| **Labeled roles per fixture ≈ 5–8** | Top-5 often covers most of the labeled set, so R@5 is high and insensitive. |
| **Tied grades** | Within-band reorderings (e.g. two grade-1 roles) leave P@k / nDCG unchanged. |
| **Hand labels** | Grades encode business-rule judgments on a synthetic ontology — not ground-truth mobility. |

Treat the macro **tie** as an honest measurement on this fixture pack, not as proof that graph edges never help ranking.

## Limitations of this evaluation

1. **Synthetic labels only** — no employee mobility outcomes.
2. **Small-n / small candidate sets** — see table above; many roles share the same grade, so reordering within a grade is invisible to P@k / nDCG.
3. **Coverage ≠ ranking win** — alias resolution changes explainability and absolute fit even when macro metrics tie.
4. **No embeddings in the measured run** — semantic similarity is out of the fit index by design (weight 0).
5. **Not a claim of production readiness** or hiring fairness.
6. **Fit scores are exploratory** — never treat them as hiring probability, person worth, or auto-decision inputs.
7. **Unproven improvements** — do not claim related-edge ranking gains, embedding lifts, or fairness properties from this eval.
