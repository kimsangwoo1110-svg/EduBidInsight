# School360 Dashboard

School360 is the primary integrated view for a selected school. It is a
read-only CustomTkinter screen introduced in Sprint 25 and does not query or
modify production business data.

## Opening School360

- Select **학교 360 / School 360** in the main navigation, choose a school, and
  double-click it.
- In normal School Search, select a result and choose **School360 열기**.
- The School Search context menu also includes **School360 열기**.

The existing school detail and legacy 360° profile remain available.

## Integrated sections

- **Basic Information:** school code, type, office, region, address, and website.
- **School Statistics:** students, classes, project totals, procurement totals,
  CRM activity, and attachment counts.
- **Planned Projects:** mock Education Office projects, schedules, and budgets.
- **Procurement:** combined mock School Market (S2B) and NaraJangteo (G2B) rows.
- **CRM:** read-only mock activity and pipeline status.
- **Attachments:** presentation-only mock document metadata.

## Connector boundary

`School360MockProvider` constructs fresh connector instances for each snapshot:

- `SchoolInfoConnector`
- `EducationConnector`
- `S2BConnector`
- `G2BConnector`
- local `MockConnector` subclasses for CRM and attachment presentation records

Each connector follows `connect → validate → fetch → disconnect`. No connector
calls `import_data()` and no record is written. The screen displays a visible
**MOCK CONNECTOR DATA** badge and lists its mock sources in the footer.

The Sprint 24 Connector Framework itself is unchanged.
