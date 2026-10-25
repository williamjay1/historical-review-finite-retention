# Canonical results

This directory contains the canonical tables, per-query details, serialized
archives, frozen inputs and artwork for the final manuscript.

- `frozen_inputs/`: 116 derived service streams, manifest and source licences.
- `static/`: 1,392 static archive files.
- `online_snapshots/`: 304 online snapshot files.
- `static_details/`, `online_details/`, `online_flush/`: per-query and
  per-closure records.
- `all_static_costs.csv`, `all_static_metrics.csv`,
  `static_task_summary.csv`, `device_task_rates.csv`: static results.
- `online_summary_b1024.csv`, `online_age_summary.csv`,
  `online_boundary_summary.csv`, `online_length_summary.csv`: online results.
- `past_policy_all_summary.csv`, `past_policy_all_forecasts.csv`,
  `past_policy_all_prefix_costs.csv`: forecast census.
- `artwork/`: figures and tables in vector and raster formats.
- `FINAL_SUBMISSION_AUDIT.json`, `PORTABLE_REPLAY_CHECK.json`,
  `core_semantic_audit.json`, `independent_semantics_audit.json`,
  `online_independent_audit.json`: verification receipts.

See `docs/DATA_DICTIONARY.md` for fields and units.
