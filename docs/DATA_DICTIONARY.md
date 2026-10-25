# Data dictionary

All paths are relative to the repository root.

## Frozen service streams

`results/revision_review_20261023/frozen_inputs/*.npz` contains 116 derived
histories: 60 coarse histories and 56 paired fine-cadence SMD histories.
`manifest.json` records each file hash, identity, atom count, channel count,
query count, header hash and source hashes. The transport NPZ size is not the
experimental retained-byte cost.

Each NPZ contains:

| Key | Meaning |
|---|---|
| `atoms` | Structured 16-byte high-record array: `t` uint32 cycle, `ch` uint16 channel, `v` uint16 context version, `q` float32 score, `x` float32 selected completed-window-last observation. |
| `high_bits` | Row-major packed high-support bitmap, little bit order. |
| `high_shape` | Shape of the support matrix. |
| `eligible_bits` | One input-usability bit per cycle. |
| `header` | Canonical UTF-8 JSON header with clock, schema, channels, threshold and provenance. |
| `queries` | Canonical evaluation query metadata. |
| `stages` | Canonical evaluation stages and annotation-derived scopes. |

Query indices use an exact arithmetic progression where possible and an
explicit int64 fallback otherwise. NPZ files contain no object arrays and are
loaded with `allow_pickle=False`.

## Static archives and details

`results/revision_review_20261023/static/*.arc` contains 1,392 serialized
static archives: 116 histories x 2 budgets x 6 methods. The binary layout is
defined by `scripts/archive_codec_20261009.py` and
`scripts/review_archive_core_20261023.py`.

`static_details/*.csv.gz` contains per-query static evaluations. Key columns:

| Column | Meaning |
|---|---|
| `dataset`, `unit`, `backbone`, `cadence` | History identity. |
| `budget`, `method`, `family` | Capacity, representation and query family. |
| `incident_id`, `channel` | Offline annotated scope identity. |
| `query_cycles` | Evaluated query cycles. |
| `positive` | Reference query has at least one high. |
| `answer` | yes, no or unknown. |
| `first_certified`, `first_numeric_joint` | First-position certificate and joint first atom success. |
| `complete_report`, `first_atom_retained`, `any_numeric` | Report and numerical availability outcomes. |
| `high_count`, `numeric_count` | Reference high and retained numerical counts. |
| `false_certificate` | Certificate disagreement flag. |

## Online snapshots and details

`online_snapshots/*.arc` contains 304 chronological snapshots.
`online_details/*.csv.gz` contains 5,280 per-query evaluations with query age,
length, support answer, first certificate, complete report, boundary crossing
and rejected-hole attribution. `online_flush/*.csv` contains per-closure
directory and payload accounting.

## Canonical summaries

| File | Unit and content |
|---|---|
| `all_static_costs.csv` | One row per history, budget and method: actual bytes, relative capacity, complete bytes, slack, retained and unsaved atoms. |
| `all_static_metrics.csv` | Static query outcomes by history, budget, method and family. |
| `static_task_summary.csv` | Pooled task outcomes by dataset, cadence, backbone, budget, method and family. |
| `device_task_rates.csv` | Device-level rates with the same cost and task columns. |
| `online_summary_b1024.csv` | 32 online conditions with queries, joint first, complete reports, unknowns, bytes, evictions and timing. |
| `online_age_summary.csv` | Online outcomes by query-age group. |
| `online_boundary_summary.csv` | Outcomes by retained-boundary stratum. |
| `online_length_summary.csv` | Outcomes by query length. |
| `past_policy_all_summary.csv` | Forecast confusion counts and errors by capacity and payload factor. |
| `past_policy_all_forecasts.csv` | Per-history, per-quarter forecast records. |
| `past_policy_all_prefix_costs.csv` | Prefix cost observations used by the forecast. |
| `tolerance_summary.csv` | Exact and tolerant first-record outcomes. |
| `complete_feasibility.csv` | Complete-storage feasibility census. |
| `article_numbers.json` | Numeric bridge from canonical results to manuscript claims. |

## Figures and tables

`artwork/` contains the two main figures and nine tables as PDF, SVG, 1200 dpi
PNG, 150 dpi previews, source data and geometry checks. The manuscript Word
tables are native and editable; the PDF/SVG table artwork is a separate
publication artifact.

## Licensing

See `DATA_LICENSE.md` and `NOTICE.md`. The frozen inputs contain source-derived
observations and are not raw datasets.
