# Reproduction guide

## Environment

Tested replay environment: Python 3.12, NumPy 2.5.1, pandas 3.0.5, zlib 1.3.1.
The replay loader itself needs only NumPy and the Python standard library.
Figure and table regeneration additionally needs the packages in
`requirements-figures.txt`.

```text
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Representative replay

From the repository root:

```text
python scripts/review_replay_frozen_20261023.py --mode static --pilot --budget-kib 256 --output replay/static_pilot
python scripts/review_replay_frozen_20261023.py --mode online --pilot --budget-kib 256 --block 1024 --output replay/online_pilot
```

The output directory must be new. The wrapper compares non-timing fields with
the canonical CSVs under `results/revision_review_20261023/` and checks archive
bytes by SHA-256. Timings are written but are not compared.

The executed verification used ESA Mission 1 ridge and the constrained SMD
ridge history at coarse and fine cadence. It produced 18 static archives and
56 online snapshot files, with all compared numerical fields equal. See
`results/revision_review_20261023/PORTABLE_REPLAY_CHECK.md` and `.json`.

A fresh replay from the public repository tree on 2026-10-25 repeated the
static pilot (18 cost rows, 36 metric rows, 18 archives) and the online pilot
(12 conditions, 56 snapshots) with comparison status `pass`. The compact
receipt is `results/revision_review_20261023/PUBLIC_REPLAY_20261025.json`.

## Full replay

The full entry points are:

```text
python scripts/review_replay_frozen_20261023.py --mode static --output replay/static_all
python scripts/review_replay_frozen_20261023.py --mode online --block 1024 --output replay/online_all
```

The full portable rerun was not executed as part of the final verification.
The original full experiments were executed in the project environment; the
canonical results are included here. The replay wrapper is the supported
portable path.

## What can and cannot be reproduced

The frozen inputs support the declared static and online archive-service
experiments. They do not contain full raw windows, low-score histories or
fitted detector objects. Arbitrary rescoring, a changed lower threshold and
bit-identical ESA fine replay from original fitted objects are outside the
package. See `docs/DATA_DICTIONARY.md` and the manuscript Section 5.4.

## Figures and tables

```text
pip install -r requirements-figures.txt
python scripts/review_figures_20261023.py
python scripts/review_table_artwork_20261023.py
```

The scripts write to `results/revision_review_20261023/artwork/`. The table
generator reads the final Markdown sources and writes PDF, SVG and 1200 dpi PNG.

## Word export

`scripts/review_export_word_v2_20261023.py` requires Pandoc on PATH and the
packages in `requirements-figures.txt`. The final layout was checked with a
Microsoft Word PDF export. LibreOffice headless misreads the fixed Word table
grid in this file.

## Verification records

- `results/revision_review_20261023/FINAL_SUBMISSION_AUDIT.json`
- `results/revision_review_20261023/PORTABLE_REPLAY_CHECK.json`
- `results/revision_review_20261023/core_semantic_audit.json`
- `results/revision_review_20261023/independent_semantics_audit.json`
- `results/revision_review_20261023/online_independent_audit.json`
- `results/revision_review_20261023/artwork/ARTWORK_PORTABILITY_CHECK.json`
