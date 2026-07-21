# EduBid Insight Personal v1.0 User Guide

## Start the application

Install the dependencies and run:

```bash
pip install -r requirements.txt
python app.py
```

At startup, EduBid Insight loads settings, configures its data and log directories, applies safe database migrations, and opens Today Dashboard.

## Today Dashboard

The home screen summarizes priority schools, today's actions, visits, overdue work, completed work, recent activity, alerts, and weekly KPIs. Use **Refresh** for an immediate update. The automatic refresh interval is configurable under Settings → Performance.

## Schools and opportunities

Use School Search to open a School 360° profile. The profile combines school information, contracts, projects, CRM activity, actions, timeline, and Opportunity recommendations.

## Import data

Open Data Source Manager, select the appropriate connector, preview the source file, confirm column mappings, and start the import. Imports support cancellation and transactional rollback.

## CRM Action Center

Create and filter visits, calls, quotations, meetings, proposals, and follow-ups. Status changes are retained in action history. Today's actions can be completed directly from Today Dashboard.

## Report Center

Choose a report type, set optional filters, and select **Print Preview**. Export becomes available after preview. Supported formats are PDF, Excel, and CSV.

## Settings

- **General:** data directory, window size, portable status, recent files.
- **Backup:** manual backup, backup listing, verified restore.
- **Performance:** dashboard refresh interval.
- **Appearance:** Light, Dark, or System theme.
- **About:** application/Python/database versions, build date, diagnostics, and release validation.

Data-directory changes apply after restarting the application.

## Portable mode

Source distributions run in portable mode automatically. For a packaged executable, place an empty `portable.flag` file beside the application or set `EDUBID_PORTABLE=1`. Portable data, backups, configuration, and logs remain under the application directory.

## Troubleshooting

Run Settings → About → **Run Diagnostics**. Review `logs/error.log` for handled failures and `logs/crash.log` for uncaught failures. Do not edit the SQLite database directly.

