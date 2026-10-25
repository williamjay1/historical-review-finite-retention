# Results and claim audit — 2026-10-23

Scope: read-only audit of `manuscript/review_results_discussion_20261023.md`, Tables 1–4, both main figures and their denominators, against executed CSVs, per-query compressed CSVs and semantic receipts in this revision. No manuscript or experimental code was changed by this audit. The separately requested Figure 1 label was changed to **Full-if-fits**, regenerated, geometrically checked and actually viewed; data and the other figure were unchanged.

**Numerical decision: PASS. No substantive numerical discrepancy found in the current revision results.** The two potentially ambiguous presentation statements below should be clarified. They do not change a result.

## Presentation points for root to resolve

1. Discussion 5.3, “Our label-independent queries and delay scenarios,” is too broad if it includes the static annotated event/channel scopes, which do use benchmark annotations. Prefer **“Our label-independent online query schedules and delay scenarios”**. Archive selection is label-independent; all query construction is not. This is a scope clarification, not a request to change the evaluation.
2. Table 4's caption says “Bytes are the final snapshot” although Table 4 contains no byte column. Remove that clause or add the intended column. The following explanation of eviction counts and run-wide p95 timings is correct.

## Independent recomputations

| Claim block | Recomputed result | Verdict |
|---|---|---|
| SMD opportunity and annotated targets | Both backbones: 327 binary incidents, 322 exactly annotated incidents, 249 coarse active opportunities and 327 fine opportunities; 2,254 annotated targets per backbone. PCA annotated-high incidents 122→216, ridge 135→224; positive target counts 749→1,101 and 932→1,228. Fine missing annotated-high incidents 322−216=106 and 322−224=98. | Matches |
| High-atom counts | PCA 24,415→238,339; ridge 111,954→1,124,754. | Matches |
| Table 1 cost census | ESA: 4 histories, fits 1/2/4 at 64/256/1,024 KiB, median/max 210,967/554,282 B. Coarse SMD: 56, fits 54/55/56, median/max 6,338/305,207 B. Fine SMD: 56, fits 36/53/55, median/max 39,840/2,743,495 B. | Matches |
| ESA event ceiling | Distinct mission/event identities in the annotated query data: 61 per backbone; positive affected-channel evidence on 8 PCA and 9 ridge identities. | Matches |
| Fine 256 KiB denominators | 4,508 queries = 2,329 positive + 2,179 negative, for each method. | Matches |
| Table 2 — complete | Joint first 2,167; complete-positive 2,167; certified negative 2,174; unknown 167. | Matches |
| Table 2 — bitmap + change | 2,180; 633; 2,179; 0, in the same column order. | Matches |
| Table 2 — bitmap + fill | 2,199; 1,521; 2,179; 0. | Matches |
| Table 2 — coverage summary | 1,912; 325; 2,161; 79. | Matches |
| Table 2 — coverage + fill | 2,123; 1,462; 2,165; 29. | Matches |
| Table 2 — full-if-fits | 2,247; 2,174; 2,179; 7. Gain against complete-only: **80 joint-first successes and 7 complete-positive reports**. | Matches |
| Fine 64 KiB comparison | Coverage summary 1,904 joint first; bitmap + change 1,777; complete 1,244. | Matches |
| Slack-fill effects | Bitmap: +19 joint first and +888 reports. Coverage: +211 joint first and +1,137 reports. Bitmap fill leaves 2,329−1,521=808 incomplete positive reports. | Matches |
| Device-level ridge heterogeneity | Over 27 positive-target devices: complete mean/min joint 0.888889/0; bitmap fill 0.932904/0.367816; full-if-fits 0.944203/0.466667. Full-if-fits minimum complete-report rate 0. | Matches rounding |
| Table 3 hard coarse device | Source 60,483 atoms, 20 positive scopes; complete required 305,207 B, declined frame 1,990 B. The five rows' byte, slack, omitted-atom and task counts agree exactly with `device_task_rates.csv`. Bitmap fill retained 4,758→16,225 atoms and joint first 13→14 without changing its two complete reports. | Matches |
| Incident 2, fine hard device, 64 KiB | Variable 10, source samples 6,013–6,015, 3 high records. Bitmap bytes 65,528, first position certified but 0 numeric atoms. Coverage bytes 49,766, one exact first atom: q=215.59866333007812, x=1, version=6. Coverage fill 65,526 B and still one record. | Matches `fine_task_case.json` |
| Tolerant versus exact-first atoms | Full-if-fits 2,259 tolerant versus 2,247 joint; coverage fill 2,188 versus 2,123. Across all positive fine annotated queries at 256 KiB, the tolerance and exact-first-atom indicators are identical **row by row**, not merely equal aggregate counts. | Matches |
| Unified online experiment | Exactly 32 conditions, 5,280 queries, 0 false certificates. All `max_bytes` values are at or below their condition's budget. | Matches |
| Table 4 hard fine device | Positive denominator 134; all-query denominator 176. Complete: 24/24/144/22; bitmap: 50/12/3/3; coverage: 56/12/0/0; adaptive: 24/6/118/21 for joint/report/unknown/evictions. p95 query timings 10.13/4.29/3.50/6.63 ms match rounding. | Matches |
| Age ≤1% | Complete 21 joint + 21 reports out of 25 positive queries; coverage 14 joint + 4 reports out of 25. | Matches |
| **Age >25%** | Positive denominator **38+24+10=72** for every policy. Coverage joint **15+4+9=28**, reports **4+2+1=7**. Complete joint and reports are both 0. Bitmap joint/reports are 25/7; adaptive 3/2. | Matches |
| Online mission examples | Mission 1 ridge, 256 KiB: bitmap 720 chunks, 56/69 joint and 48 reports, 0 unknown; complete 42/42 with 36 unknown; coverage 38/33 with 25 unknown. Mission 1 PCA, 64 KiB: complete joint 22/65, bitmap 17, coverage 10. | Matches |
| Chunk-size sensitivity | Hard fine complete at 64 KiB rejects 20 chunks at block 1,024 and 0 at block 256; block-256 unknowns 149/176 at 64 KiB and 115/176 at 256 KiB; coverage unknowns 0 at the latter cap. Smaller-chunk positive denominator is 143, unlike 134 for block 1,024; manuscript correctly avoids a paired task-effect comparison. | Matches |
| Resource measurements | Hard fine peak open payload 522,928 B; complete 256 KiB tracked transient 841,448 B; query p95 range 3.50–10.13 ms; close p95 39.22–297.48 ms. Mission 1 ridge complete query p95 87.65 ms. Query code reopens the file and decodes intersecting retained chunks. | Matches |
| Past-only forecast census | 116 histories × 3 next-quarter evaluations = 348 decisions per budget/margin. At 64 KiB, false-feasible/false-infeasible 15/2 unbuffered and 11/4 buffered. At 256 KiB 4/1 and 4/3. Fine SMD contributes 13 of the unbuffered 64 KiB false-feasible decisions. | Matches |
| Forecast growth examples | Mission 1 ridge 19,943→274,131 B at quarters 1→2; fine machine-1-1 PCA 8,154→100,580 B at quarters 2→3. Maximum underforecast 0.917042 (91.7%); buffered 0.899403 (89.9%). | Matches |
| Finite-domain certificates | Core 28,672 subset queries, 0 false certificates, 0 avoidable unknown; independent multichannel 32,768 checks, 0 false/avoidable certificates. Both receipts refer to frozen core SHA256 `6ffa3462733abd162d9a6d612464ef5bec9ead680335b0f9d83330d36d44d637`. | Matches |
| Serialized real-file checks | 1,392 archive files = 116 histories × 2 budgets × 6 methods. The 116 per-history detail CSVs contain 213,624 query evaluations and 0 false-certificate indicators. Their unusable-cycle sum is 0, agreeing with the manuscript's distinction between real-grid and constructed unavailable-input checks. | Matches |

## Figure, denominator and claim checks

- Figure 1a deduplicates the cost table to 56 coarse SMD, 56 fine SMD and four ESA histories. ESA is an individual rug rather than a pooled ECDF. The 1 MiB guide is a feasibility threshold rather than a separately optimized capacity run.
- Figure 1b uses only the fine SMD `full_annotated` workload at 256 KiB, with the same 2,329 positive-query denominator for both services and all six methods. The label is now **Full-if-fits**. Distinct outcome markers and their small vertical separation do not change values.
- Figure 2 uses the block-1,024 hard fine history at 256 KiB, not the block-256 sensitivity. Age-bin denominators are 25/37/38/24/10 and sum to 134 positive queries for every policy. No all-query unknown rate is plotted as a positive-query rate. Both axes use 0–1.
- The text correctly avoids treating fits/backbones/queries as independent incidents, avoids significance claims, and keeps the static all-or-refuse reference separate from online retention. The failure of adaptive online service and incomplete older reports is visible in the main results.
- Byte forecasts are properly described as planning errors rather than guarantees or operational risk estimates; synthetic unavailable-input checks are not represented as real missing-data validation; tracked memory is not presented as total RAM; query timing is not a service-level guarantee.
- No further overgeneralization requiring a results correction was found. The legacy 36-byte experiment, old notification losses and licensing statements are outside this fresh numerical audit and should continue to rely on their existing source/verification records.

## Source scope

Main independent calculations used `all_static_costs.csv`, `static_task_summary.csv`, `device_task_rates.csv`, `fine_stream_cost.csv`, all 116 `static_details/*.csv.gz`, `online_summary_b1024.csv`, `online_age_summary.csv`, `online_pilot_b256.csv`, `past_policy_all_summary.csv`, `past_policy_all_prefix_costs.csv`, `fine_task_case.json`, `core_semantic_audit.json` and `independent_semantics_audit.json`. Existing aggregate `article_numbers.json` was not used as the numerical oracle. Both new figure previews were actually inspected after the requested Figure 1 label change, with source values checked from CSVs rather than read visually.
