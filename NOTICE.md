# Third-party notices

## ESA-ADB version 2

The ESA-derived records are adaptations of the ESA Anomaly Dataset, version 2,
released by the European Space Agency and the ESA-ADB benchmark contributors:

- Dataset record: https://zenodo.org/records/15237121
- DOI: https://doi.org/10.5281/zenodo.15237121
- Project: https://github.com/kplabs-pl/ESA-ADB
- License: CC BY 3.0 IGO, https://creativecommons.org/licenses/by/3.0/igo/

Changes made for this study include frozen detector scoring, threshold-based
selection of high records, cycle indexing, review-context tags and selection of
completed-window-last observations. The released timestamps have an anonymizing
affine transformation and do not establish physical spacecraft deadlines. No
endorsement by ESA or the benchmark contributors is implied.

## Server Machine Dataset

The SMD-derived records are adaptations of the Server Machine Dataset from
NetManAIOps/OmniAnomaly, fixed revision
`7fb0e0acf89ea49908896bcc9f9e80fcfff6baf4`:

- Source: https://github.com/NetManAIOps/OmniAnomaly
- Dataset license: MIT, copyright 2021 NetManAIOps-SMD
- License copy: `results/revision_review_20261023/frozen_inputs/licences/SMD_DATASET_LICENSE.txt`

Changes include the same scoring, high-record selection and cadence
transformations. The interpretation labels are used for offline query scopes,
not as physical causal-root ground truth.

## Figure style

The figure style helper follows the public SciencePlots project, MIT license,
revision `b9b16959570bd2fbc9ff5118bacc423c3bddd592`. No SciencePlots source is
redistributed here; the local `figstyle.py` helper is project code.

## Software

The code imports NumPy, pandas, matplotlib, Pillow and PyMuPDF. These packages
are not redistributed. Their own licenses apply to installed copies.

## No raw data

No original ESA-ADB or SMD archive is redistributed. The repository contains
derived service records, serialized test archives, canonical results and code.
