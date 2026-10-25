# Portable frozen-input replay: executed verification

Status: **PASS for the stated representative scope**. The frozen core was not edited. This does not claim a new 116-stream portable rerun, detector refitting, or reconstruction from the original raw datasets.

The wrapper is `scripts/review_replay_frozen_20261023.py`. It loads the portable service records with `review_frozen_inputs_20261023.load_stream`, then calls the existing `review_experiments_20261023.static_one` or `review_online_20261023.run_one`. Output paths, budgets and online chunk size are redirected only in memory. Every call requires a previously nonexistent output directory and refuses an output under the frozen inputs.

## Actual completed runs

| Run | Selection | Budget | Conditions / metric rows | Exact archives | Compared non-timing CSV files / rows | Result |
|---|---|---:|---:|---:|---:|---|
| Representative static | ESA Mission 1 ridge; SMD machine-3-4 ridge at coarse and fine cadences | 256 KiB | 18 cost rows, 36 family metric rows | 18 | 3 / 4,770 | PASS |
| Representative online | The same three streams; four policies; block 1,024 | 256 KiB | 12 conditions | 56 snapshots | 24 / 4,924 | PASS |
| Isolated code root, with filesystem guard | SMD machine-3-4 ridge, fine cadence; six static policies | 256 KiB | 6 cost rows, 12 family metric rows | 6 | 1 / 576 | PASS |

All actual summary rows were compared with their canonical counterparts. Timings were excluded; all other numerical fields were checked with relative and absolute tolerance 1e-12, and stored archive bytes were checked by SHA-256 equality. CSV row counts in the table cover query and flush detail files, and are not independent incidents. Exact per-run paths, hashes and elapsed times are in `PORTABLE_REPLAY_CHECK.json` and the individual `replay_completion.json` files.

The first static receipt reported a row-count failure because its 256-KiB detail output was compared against a canonical detail file containing both 64- and 256-KiB rows. The comparator now selects matching condition groups before comparison. The saved experimental results were unchanged; their recheck passed. The execution and corrected-comparator hashes are recorded separately.

## Isolation and dependencies

Twelve local Python modules were copied into `<isolated-code-root>`. That root had no `raw`, `cache`, `datasets`, `venv` or `checkpoints` directories. The final guarded replay allowed file access only within this isolated root, the frozen inputs, canonical static result files used as a read-only comparison reference, or C: system/runtime files. E: and F: data drives and the original project scripts/cache/datasets were blocked. It completed with 503 recorded file-open events (79 under the project), zero unexpected accesses and zero E:/F: opens. The filesystem receipt records all audited paths up to its serialization; the receipt write itself is excluded. Earlier unguarded and project-guarded runs of the same condition also passed. Small verification receipts were copied, without moving their originals or copying canonical archives, into `portable_isolation_receipts/`; their package-relative locations and copy hashes are recorded in the JSON report and `portable_isolation_receipts/isolation_copy_manifest.json`.

The replay requires Python, NumPy and pandas, plus Python's standard library (including zlib). SciPy, scikit-learn, PyTorch and plotting libraries are not required by this replay path. The conservative recursive AST closure includes optional source-adapter/export imports because they occur in the reused modules; those source-loader functions were not executed. `PORTABLE_IMPORT_CLOSURE.json` lists all twelve files and their hashes.

Tested environments:

- Original representative runs: Python 3.12.10, NumPy 2.5.1, pandas 3.0.5, zlib 1.3.1.
- Isolated guarded run: Python 3.12.14, NumPy 2.3.5, pandas 3.0.1, zlib 1.3.2.

These are tested versions, not a claimed lower version bound. Archive-byte equality held in both environments for the reported condition.

## Commands from a distributed code root

The following commands use the default relative location `results/revision_review_20261023/frozen_inputs`; change `--inputs` if the bundle is stored elsewhere. Each output directory must be new. A reference directory is read only; use `--reference` to point to the canonical result directory if it is not at its default location. If references are absent, the wrapper reports comparison `not_run` instead of claiming a match.

```text
python scripts/review_replay_frozen_20261023.py --mode static --pilot --budget-kib 256 --output results/portable_static_pilot_new
python scripts/review_replay_frozen_20261023.py --mode online --pilot --budget-kib 256 --block 1024 --output results/portable_online_pilot_new
```

The following larger commands are supported, but were **not** executed as new portable full reruns in this verification:

```text
python scripts/review_replay_frozen_20261023.py --mode static --output results/portable_static_all_new
python scripts/review_replay_frozen_20261023.py --mode online --block 1024 --output results/portable_online_all_new
```

Static defaults to all 116 streams, six original methods and 64/256-KiB caps. Online defaults to the four canonical streams (ESA Mission 1 PCA/ridge and SMD machine-3-4 ridge at coarse/fine cadences), four original policies and 64/256-KiB caps. `--pilot` limits either mode to the three ridge streams above. `--unit`, `--cadence`, `--backbone`, `--budget-kib` and `--block` allow explicit selection without changing the frozen core.

## Files to include in the portable code closure

- `archive_codec_20261009.py`
- `archive_task_audit_20261009.py`
- `evidence_representation_audit.py`
- `notification_design.py`
- `notification_workflow_analysis.py`
- `review_archive_core_20261023.py`
- `review_experiments_20261023.py`
- `review_fine_stream_20261023.py`
- `review_frozen_inputs_20261023.py`
- `review_online_20261023.py`
- `review_replay_frozen_20261023.py`
- `revision_decision_audit.py`

All 116 NPZ inputs were exported and reopened exactly, totalling 15,404,641 bytes. The input bundle contains derived high-score atoms, bitpacked support/usability, headers, query indices and metadata, and stages. Selected original window-last observations remain inside these derived atoms. It does not include full raw datasets, all observations, all windows, below-threshold records, or fitted detectors. Source attribution and dataset licence information remain required; see the frozen-input README and `SOURCE_AND_RIGHTS.md`.
