[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23646555.svg)](https://doi.org/10.5281/zenodo.23646555)

# Historical review under finite monitoring retention

Code, derived data, serialized archives, canonical results and manuscript
sources for:

**Historical review under finite monitoring retention: Complete compression,
semantic summaries and service boundaries**

This is the public reproducibility repository for the manuscript. The archived
release is available at https://doi.org/10.5281/zenodo.23646555 (version
v1.0.0).

## What the study asks

Historical review of anomaly monitoring outputs asks for the first threshold
crossing, its logged value, or every high record in an interval, often after
the stream has been compressed or expired. The study compares six retention
designs on two executable review tasks under one 16 byte record contract and
identical byte budgets. It uses 116 histories from 28 server devices and two
spacecraft missions, 1,392 serialized static archives, and 32 chronological
online conditions with 5,280 queries.

## What is in this repository

- `manuscript/`: final main manuscript, supplementary material, cover letter,
  and their Markdown sources.
- `scripts/`: archive codec, static and online experiment drivers, portable
  replay, independent audits, figure and table generators, and Word export.
- `results/revision_review_20261023/frozen_inputs/`: 116 derived service
  streams in NPZ form, with manifest, schema notes and source licences.
- `results/revision_review_20261023/static/`: 1,392 serialized static archive
  files.
- `results/revision_review_20261023/online_snapshots/`: 304 serialized online
  snapshot files, with `online_details/` and `online_flush/`.
- `results/revision_review_20261023/`: canonical cost, task, online, forecast,
  tolerance and audit tables, including per-query details.
- `results/revision_review_20261023/artwork/`: 2 figures and 9 tables as PDF,
  SVG, 1200 dpi PNG, source data and geometry checks.
- `docs/`: data dictionary, reproduction guide, source and rights notes, and a
  suggested data and code availability statement.

## Quick start

Requirements: Python 3.12 or later.

```text
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/review_replay_frozen_20261023.py --mode static --pilot --budget-kib 256 --output replay/static_pilot
python scripts/review_replay_frozen_20261023.py --mode online --pilot --budget-kib 256 --block 1024 --output replay/online_pilot
```

The pilot uses ESA Mission 1 ridge and the constrained SMD ridge history at
coarse and fine cadence. It writes new archives and compares their non-timing
fields with the canonical results in this repository. Timings are not expected
to match across machines.

The full replay entry points are:

```text
python scripts/review_replay_frozen_20261023.py --mode static --output replay/static_all
python scripts/review_replay_frozen_20261023.py --mode online --block 1024 --output replay/online_all
```

The full portable rerun was not part of the recorded verification; the
representative pilot was. See `docs/REPRODUCTION.md` and
`results/revision_review_20261023/PORTABLE_REPLAY_CHECK.md`.

## What is not included

- Raw ESA-ADB or SMD archives. These remain at their official sources.
- Fitted detector objects and original training caches. The frozen scores and
  selected service records are included, but arbitrary rescoring and a changed
  lower threshold are outside this package.
- Human-subject data. No human participants were recruited.

## Data and code availability

Statement used in the manuscript:

> The code, 116 frozen service streams, 1,392 serialized static archives, 304
> online snapshot archives, canonical result tables, figure and table source
> data, and reproduction instructions are available at
> https://github.com/williamjay1/historical-review-finite-retention. The release
> is archived at https://doi.org/10.5281/zenodo.23646555.

The manuscript data statement uses this single release DOI. See
`docs/DATA_AVAILABILITY.md`.

## Licenses

- Code: MIT, see `LICENSE`.
- Project-created documentation, metadata and figure source data: CC BY 4.0,
  see `DATA_LICENSE.md`.
- ESA-ADB derived material: CC BY 3.0 IGO.
- SMD derived material: MIT, copyright 2021 NetManAIOps-SMD.

See `NOTICE.md` for attribution and changes.

## Citation

Cite the manuscript and the archived release:

> https://doi.org/10.5281/zenodo.23646555

## Contact

Open a GitHub issue for questions about the code or data.
