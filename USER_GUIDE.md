# EduBid Insight Personal v1.0 User Guide

## Sprint 26: School360 예정사업 관리

School360의 `예정사업` 카드에서 선택한 학교의 사업을 관리할 수 있습니다.

1. `사업 추가`를 눌러 사업명, 상태, 예산, 사업 기간, 예상 조달일과 메모를 입력합니다.
2. 등록된 사업의 `수정` 또는 `삭제` 버튼으로 내용을 관리합니다.
3. 여러 사업을 한 번에 등록하려면 `양식 다운로드`로 공식 Excel 양식을 받은 뒤
   `예정사업 가져오기`를 선택합니다.
4. 같은 사업명의 행은 기존 사업을 갱신하고, 새로운 사업명은 새로 등록합니다.
5. 잘못된 상태·예산·연도·날짜가 있는 행은 저장하지 않고 결과 요약에 표시합니다.

## Start the application

For the Windows release, run `EduBidInsight.exe`. No Python installation is required.

To run from source instead:

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

Open **Excel Import Center** from Data Sources and choose School, Education Office, School Market, NaraJangteo, or CRM. Download the official workbook from **Template Center**, or select/drag an existing `.xlsx` or `.csv` file into the wizard.

The wizard proceeds through Select File → Analyze Workbook → Preview Data → Validate → Import → Summary. Korean and English column aliases are mapped automatically and can be corrected before validation. Invalid rows appear in a soft red highlight and can be exported to a separate Excel workbook for correction. The history table records the date, source, analyzed rows, successes, failures, duration, and final status.

Existing transactional connectors retain their cancellation and rollback behavior. Always review the validation page before importing production data.

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

## Windows executable data

The production `EduBidInsight.exe` uses installed mode and stores writable settings, database, backups, imports, and logs under `%LOCALAPPDATA%\EduBidInsight`. The clean `config`, `data`, and `backups` folders in the release package are deployment/reference folders and contain no customer information.

Source checkouts continue to run in portable mode. Advanced deployments can override packaged storage with the `EDUBID_PORTABLE` environment setting, but the standard Windows release should use its default installed-mode location.

## Troubleshooting

Run Settings → About → **Run Diagnostics**. Review `logs/error.log` for handled failures and `logs/crash.log` for uncaught failures. Do not edit the SQLite database directly.
