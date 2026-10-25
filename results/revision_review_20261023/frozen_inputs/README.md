# Frozen archive-service inputs

This portable package contains 116 executed source histories: 60 coarse histories
(56 SMD device/backbone combinations and four ESA mission/backbone combinations)
plus the 56 paired fine-cadence SMD histories. It is sufficient to rerun the
declared static archive-service tasks without accessing original local raw-data
paths. No detector is fitted by export or loading.

These are **derived service records**, not the complete original raw datasets.
Each structured atom preserves the recorded cycle, channel, context version,
float32 score and selected original completed-window-last observation. The last
field is a selected source observation; it is not a synthetic value. The package
does not include full windows, below-threshold numeric histories or fitted model
objects, and cannot reproduce arbitrary rescoring or a changed lower threshold.

Per NPZ: `atoms` is the exact structured 16-byte high-record array; `high_bits`
is row-major support packed with little bit order; `high_shape` gives its shape;
`eligible_bits` separately stores one input-usability bit per cycle. Canonical
UTF-8 JSON preserves the charged header, evaluation stages and query metadata.
Query index arrays use an exact arithmetic progression where possible and an
explicit int64 fallback otherwise. The query `hits` array, when present in the
source, is restored exactly from its frozen scope and high-support array. NPZs
contain no object arrays and are read with `allow_pickle=False`.

Use `load_stream(path)` from `scripts/review_frozen_inputs_20261023.py`. Loading
requires only NumPy and Python's standard library, and does not import the source
adapters. The result provides `a`, `h`, `eligible`, `header`, `queries`, `stages`
and dataset/unit/backbone/cadence identity. Every written file was reopened and
checked for byte-exact atoms, exact support/usability, exact query indices and
metadata, and canonical-equivalent header/stages. `manifest.json` contains file
hashes and the core/loader/exporter source hashes. Package byte counts are NPZ
transport sizes, **not** the budgeted archive sizes reported by the experiment.

Annotation-derived event/channel scopes and stages are offline evaluation inputs.
The lossless package preserves them for reproduction; they must not be passed to
online retention or compression decisions. The fixed grid queries are separate.
Fine and coarse streams retain their distinct cycle clocks; ESA released times
are transformed benchmark coordinates and do not establish physical deadlines.

## Attribution and licences

ESA inputs are derived from ESA-ADB v2, released by the European Space Agency and
benchmark contributors at https://zenodo.org/records/15237121 . Original dataset
and benchmark: https://github.com/kplabs-pl/ESA-ADB and De Canio et al., *The ESA
Anomaly Dataset: Advancing Telemetry Anomaly Detection*,
https://arxiv.org/abs/2406.17826 . Data are subject to CC BY 3.0 IGO:
https://creativecommons.org/licenses/by/3.0/igo/ . Retain credit and the licence
link and comply with its IGO-specific terms. Changes include frozen detector
scoring, threshold selection of records, cycle indexing, feedback-context tags
and selection of last-window observations. No ESA endorsement is implied. The
repository code licence does not replace the data licence.

SMD inputs are derived from the Server Machine Dataset, NetManAIOps/OmniAnomaly,
fixed repository revision 7fb0e0acf89ea49908896bcc9f9e80fcfff6baf4. The separately
verified dataset-specific MIT licence (copyright 2021 NetManAIOps-SMD) and its
source receipt are retained under `licences/`. These are the dataset licence,
not an inference from the repository code licence. Retain its copyright and
permission notice when redistributing copies or substantial portions. Derived
changes are the same scoring/record selection and cadence transformations
described above; SMD interpretation labels provide offline query scopes rather
than physical causal-root ground truth.

This package is part of the public reproducibility repository. See the root README,
DATA_LICENSE.md and NOTICE.md for the source terms and release status.
