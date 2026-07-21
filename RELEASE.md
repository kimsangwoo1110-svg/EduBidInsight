# EduBid Insight v1.0.0

EduBid Insight v1.0 includes Smart Import, SchoolMarket/G2B/Education Office connectors, School 360°, Opportunity Engine, CRM Action Center, Today Dashboard, and Report Center.

Report Center supports School, Opportunity, CRM, Weekly, Monthly, and Executive reports with print preview and PDF, Excel, or CSV export.

## Runtime

- Python 3.10 or newer
- Dependencies listed in `requirements.txt`
- SQLite database initialized automatically by `app.py`

## Release verification

```bash
pip install -r requirements.txt
python -m pytest -q -p no:cacheprovider
python app.py
```

The automated release gate requires the complete test suite and module compilation to pass before packaging.
