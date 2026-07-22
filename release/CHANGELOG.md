# Changelog

## 1.0.0 — 2026-07-21

### Excel Import Center

- Added five official templates for School, Education Office, School Market, NaraJangteo, and CRM imports.
- Added a six-stage Select, Analyze, Preview, Validate, Import, and Summary workflow.
- Added automatic Korean/English column aliases, invalid-row highlighting, failed-row export, and drag-and-drop.
- Added persistent import audit details for row totals, successes, failures, and duration without changing the database schema.

### Windows release packaging

- Added a windowed, console-free PyInstaller build for `EduBidInsight.exe`.
- Added Windows product metadata, multi-resolution application icons, and taskbar identity.
- Added one-command release assembly with startup, database, backup, dashboard, and report smoke checks.
- Added a generated PDF user guide and clean production release directory structure.

### Operations and release

- Added persistent JSON settings and automatic portable-mode detection.
- Added manual and exit backups, verified restore, and seven-backup retention.
- Added transactional schema version tracking with file-level rollback.
- Added database, directory, disk, dependency, and release diagnostics.
- Added rotating application, import, error, and crash logs.
- Added Settings, Backup, Performance, Appearance, and About screens.
- Added the v1.0 release validator and operational documentation.

### Reporting and daily workflow

- Added Report Center with PDF, Excel, and CSV export.
- Added Today Dashboard, CRM Action Center, and Opportunity Engine.
- Added School 360° profiles with unified timelines and recommendations.

### Data integration

- Added Smart Import with preview, mapping, cancellation, rollback, and summaries.
- Added SchoolMarket, G2B, and Education Office connectors.
