# Evaluation

Measured on **2026-10-21** against the seeded local demo (`GET /api/evaluation`, `method_version=skg-baseline-1.0.0`, `dataset_version=gold-fixtures-1.1.0`, embeddings **disabled**).

## What is being measured

| Item | Policy |
| --- | --- |
| Fixtures | Ten hand-labeled synthetic profiles in `app/domain/gold.py` |
| Candidate set | Only roles listed in each fixture’s `labels` map; unlabeled roles excluded |
| Relevance | Fixture grades 3 / 2 / 1 / 0 — business-rule judgments on the ontology, **not** hiring outcomes |
| Relevant for P@k / R@k | grade > 0 |
| **Overlap baseline** | Asserted label must equal the requirement’s **canonical** name after normalize — **no** alias table, **no** related edges, **no** level weighting (`overlap_baseline_score`) |
| **Graph-augmented** | Exact + validated synonym + related/broader/narrower soft credit (`score_profile_against_role`) |
| Rank key | Method score descending, then role title ascending (stable tie-break) |
| Metrics | Macro average of Precision@3/5, Recall@3/5, nDCG@3/5 over the ten fixtures |
| Tie reporting | `macro_metrics_tie` plus per-profile `ranking_grade_ties` in the API payload |

Grades were assigned from explicit rules (primary role vs stretch vs no transfer) and are **not** copied from the scorer. Fit / coverage scores are exploratory indices — never job-offer probabilities.

## Fixture scenarios (`gold-fixtures-1.1.0`)

| Id | Scenario | Intent |
| --- | --- | --- |
| synonym_specialist | (legacy) | Alias identity vs overlap miss |
| data_analyst_demo | (legacy) | Dense analyst profile |
| qa_manual | (legacy) | Manual QA focus |
| automation_ready | (legacy) | Automation / SDET |
| cloud_admin | (legacy) | Ops / DevOps |
| alias_heavy | alias-heavy | Many stored aliases |
| cold_start | cold-start | Minimal skills |
| missing_mandatory_gap | missing-mandatory | Identity on some skills; mandatory gaps remain |
| misleading_related | misleading-related | Strong related neighbors without role readiness |
| multi_role_ambiguous | multi-role | Several grade-3 QA-family roles |

## Macro results (actual)

| Method | P@3 | P@5 | R@3 | R@5 | nDCG@3 | nDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Overlap baseline | 0.8667 | 0.8400 | 0.5175 | 0.9092 | 0.8152 | 0.8908 |
| Graph-augmented | 0.9000 | 0.8400 | 0.6175 | 0.9092 | 0.9383 | 0.9684 |

**`macro_metrics_tie=false` on this expanded set.** Graph is higher on P@3, R@3, nDCG@3, and nDCG@5; P@5 and R@5 still match. This is a measured outcome on synthetic labels — **not** a hiring-outcome claim and **not** proof that related edges generalize.

On the original five fixtures alone (pre-expansion), macros **tied**. Divergence is driven by the new cold-start / missing-mandatory / misleading-related profiles, where top-k **grade sequences** differ (`ranking_grade_ties` false). The other seven fixtures still show identical top-3 and top-5 grade sequences for graph vs overlap.

## Honest read

1. **Do not hide the non-tie.** Report API fields `macro_metrics_tie` and `tie_note` as returned.
2. **Do not treat coverage deltas as ranking wins** when grade sequences still match (legacy five + alias_heavy + multi_role).
3. **Related / semantic credit never satisfies mandatory gates** — verified in unit and fault-injection tests. Ranking movement ≠ mandatory satisfaction.
4. **Fixtures were not tuned post-hoc** to invent a graph win: scenario labels follow the same grade rules as the original set.
5. Related-edge ranking gains remain **fragile** on a tiny labeled catalog; treat nDCG lifts as exploratory.

## Ranking-order check (grade sequences)

| Fixture | Top-3 / Top-5 grades identical (graph vs overlap)? |
| --- | --- |
| synonym_specialist | yes / yes |
| data_analyst_demo | yes / yes |
| qa_manual | yes / yes |
| automation_ready | yes / yes |
| cloud_admin | yes / yes |
| alias_heavy | yes / yes |
| cold_start | **no / no** |
| missing_mandatory_gap | **no / no** |
| misleading_related | **no / no** |
| multi_role_ambiguous | yes / yes |

## Limits

| Limit | Implication |
| --- | --- |
| Synthetic grades | Not employee or hiring ground truth |
| Small candidate sets | Easy for metrics to jump when one grade swaps |
| Overlap is harsh | Canonical-name equality only; alias lifts are expected on coverage |
| No held-out production traffic | Demo evaluation only |

Full scoring rules: [ALGORITHM.md](ALGORITHM.md). Latency samples: [PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md).
