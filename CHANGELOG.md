# Changelog
This format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- Update to SWGS app, including display of coverage, CNVs, SVs, fusions

## [v1.6.3] - 24/04/2025

### Added
- New breast panel for ctDNA (ESR1 only)
- Copy and paste button for HGVS c. and p,

### Changed
- Update panel fixtures

## [v1.6.2] - 31/03/2025

### Fixed
- Bug when making a new user

### Changed
- Update panel fixtures

## [v1.6.1] - 21/03/2025

### Added
- Add download for clinical scientist checks

### Changed
- Update panels

## [v1.6.0] - 2024-11-20

### Added
- variant validator checks to poly and artefact lists

### Changed
- Update config for deploy on Wren webserver Wren Webserver deploy

## Fixed
- gnomad links as the format has changed Gnomad link
- errors in poly list command and links in documentation

## [v1.5.0] - 2024-08-21

### Added
- Download button to download whole worksheet coverage TSV
- Added initial SWGS page in background

## [v1.4.4] - 2024-07-04

### Added
- Tickbox for users to confirm they've checked IGV settings before starting sample analysis
- `docs` folder that renders documentation with docsify
- Added this changelog, filled from info in releases
- Synced across MCL panel from live database (fixtures and bed file)

### Changed
- Moved the pull request template to `.github` directory

## [v1.4.3] - 2024-04-18

### Removed
- ajax_num_pending function removed from homepage

## [v.1.4.2] - 2024-03-11

### Fixed
- Users can now add variants up to 20bp outside of ROIs to be allowed for overlapping indels to be input correctly

## [v1.4.1] - 2024-01-12

### Fixed
- Fixed bug where gene names were not included in gaps on the PDF report

## [v1.4.0] - 2024-01-07

### Added
- Automated unit testing in GitHub for commits and pull requests
- Unit tests for data upload
- Form validation for inputting of manual variants to enforce genomic nomenclature
- Functionality for manual fusion input
- Functionality for fusion artefacts
- Home page

### Changed
- Updates to LIMS XML download

### Fixed
- Fully fixed bug where fusions were not being uploaded correctly
- Fixed bug where gnomAD link was incorrect
- Fixed bug where fusion checks were in wrong order
- Fixed bug where fusions were not consistently displayed
- Fixed bug where manual variants were added multiple times on page refresh

## [v1.3.0] - 2023-11-21

### Added
- Support for CRM/BRCA upload

### Changed
- Functionality for artefact lists specific to each assay

### Fix
- Hotfix for bug where fusions were not being uploaded correctly

## [v1.2.2] - 2023-09-18

### Added
- Ability to set user LIMS initial
- Password reset form

### Changed
- Changes to LIMS XML format

## [v1.2.1] - 2023-08-01

### Added
- Ability for users to reopen a case that they have finalised
- LIMS XML download
- "Options" page for poly lists etc.
- Added COSMIC counts to report tab and PDF download
- Tests for COSMIC build 38 data
- Added error handling in upload script to prevent duplicate run uploads under different IDs

### Changed
- Included search by sample in the worksheets page
- Altered PDF formatting including adding page numbers
- Display "No calls" or "No gaps" in reports rather than an empty table where there are no gaps/variants

### Fixed
- Fixed issue where the incorrect analysis tab was loaded
- Fixed bug where COSMIC data could not be imported with different kinds of null data

## [v1.2.0] - 2023-03-29

### Added
- Functionality for build 38

### Changed
- Altered database for ctDNA

### Fixed
- Fixed bugs where samples would fail upload if there is no coverage
- Prevented manual uploads with a total depth of 0

## [v1.1.2] - 2022-12-20

### Added
- Added checks before first analysis to confirm that the referral is correct
- First check fails can now be unassigned

### Changed
- Changed the filtering on the worksheets page so diagnostic and training runs are split, and only the 30 most recent runs are shown by default
- VAF is now rounded to 2dp for analysis page and whole number for report pages
- Increased comment box character restriction
- Wording altered for check finalisation

## [v1.1.1.] - 2022-11-08

### Fixed
- Fixed bug where myeloid coverage was not calculated correctly

## [v1.1.0] - 2022-11-08
 
### Added
- Added myeloid referrals

## [v1.0.0] - 2021-11-15

### Added
- Initial release
