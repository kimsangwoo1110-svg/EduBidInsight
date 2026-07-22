# EduBid Insight v1.0.0

EduBid Insight v1.0 includes Smart Import, SchoolMarket/G2B/Education Office connectors, School 360°, Opportunity Engine, CRM Action Center, Today Dashboard, and Report Center.

Report Center supports School, Opportunity, CRM, Weekly, Monthly, and Executive reports with print preview and PDF, Excel, or CSV export.

## Runtime

- `EduBidInsight.exe` is a self-contained, windowed Windows application.
- Python is not required on end-user computers.
- Writable data is initialized automatically under `%LOCALAPPDATA%\EduBidInsight`.

## Release verification

```bash
python -m pip install -r requirements-build.txt
python build.py
```

The release build runs the complete test suite, creates the EXE and PDF guide, assembles `release/`, validates Windows metadata, launches the executable, verifies first-run settings and database creation, closes it normally to verify backup creation, and exports PDF, Excel, and CSV smoke-test reports.
