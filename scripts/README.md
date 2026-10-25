# Code

The code is organized around the final archive-service experiments.

## Portable replay

- `review_replay_frozen_20261023.py`: replay static or online policies from the
  116 frozen service streams.
- `review_frozen_inputs_20261023.py`: NPZ loader and schema checks.
- `review_archive_core_20261023.py`: archive codec and certification core.
- `review_experiments_20261023.py`: static experiment driver.
- `review_fine_stream_20261023.py`: paired fine-cadence construction.
- `review_online_20261023.py`: chronological online driver.

The replay imports a conservative closure including
`archive_codec_20261009.py`, `archive_task_audit_20261009.py`,
`evidence_representation_audit.py`, `notification_design.py`,
`notification_workflow_analysis.py` and `revision_decision_audit.py`.

## Audits

- `review_independent_semantics_20261023.py`: independent finite-world
  semantics audit.
- `audit_final_submission_20261023.py`: manuscript compliance audit.
- `results/revision_review_20261023/online_independent_audit.py`: independent
  online audit.

## Artwork and Word

- `review_figures_20261023.py`: Figure 1 and Figure 2.
- `review_table_artwork_20261023.py`: nine vector tables.
- `figstyle.py`: shared figure style and geometry checks.
- `review_export_word_v2_20261023.py`: Word export; requires Pandoc on PATH.

The original source adapters used to build the frozen inputs are not included
as a supported path because the original raw caches and fitted model objects
are not redistributed. Use the frozen-input replay for the public reproduction.
