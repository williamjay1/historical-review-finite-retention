# Zenodo deposit notes

The GitHub repository is public and release-ready. The authors create the
Zenodo archive and DOI after this upload.

## Suggested metadata

- Title: Historical review under finite monitoring retention: Complete
  compression, semantic summaries and service boundaries
- Upload type: Software or Dataset
- Keywords: anomaly monitoring; historical review; finite retention; query
  completeness; time series; compressed storage; reproducibility
- License: CC BY 4.0 for project-created documentation and data; source terms
  apply to ESA-ADB and SMD derived material. See `DATA_LICENSE.md`.
- Related identifiers:
  - GitHub repository: https://github.com/williamjay1/historical-review-finite-retention
  - Manuscript: add the article DOI when available
  - ESA-ADB: https://doi.org/10.5281/zenodo.15237121
  - SMD: https://github.com/NetManAIOps/OmniAnomaly

Add the author list, affiliations, ORCID iDs and funding information in the
Zenodo form. The repository does not contain author identity metadata.

## Release steps

1. Create a GitHub release from tag `v1.0.0` (do not create the release before
   the author list and license are confirmed).
2. If the repository is not yet enabled in Zenodo, switch it on at
   https://zenodo.org/account/settings/github/
3. Publish the release. Zenodo archives the repository snapshot and mints a
   version DOI and a concept DOI.
4. Add the version DOI to `README.md`, `docs/DATA_AVAILABILITY.md` and the
   manuscript data statement.
5. Use the concept DOI for "all versions" and the version DOI for the exact
   release.

## Scope

The GitHub snapshot contains code, derived service records, serialized
archives, canonical results, figures and manuscript sources. It does not
contain raw ESA-ADB or SMD data. The archive is a reproducibility package, not
a redistribution of the source datasets.
