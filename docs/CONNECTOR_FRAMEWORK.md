# Connector Framework

Sprint 24 introduces a transport-only connector layer under `connectors/`.
It does not replace or modify EduBid Insight business services. Connectors
retrieve source records and hand them to an injected importer; domain services
remain responsible for validation and persistence.

## Lifecycle

Every connector implements the same contract:

1. `connect()` opens a file, session, or remote transport.
2. `validate()` checks configuration and source availability.
3. `fetch()` returns normalized source dictionaries without database writes.
4. `import_data(records)` delegates to an injected importer.
5. `disconnect()` releases resources and is always called.
6. `sync()` orchestrates the complete lifecycle and returns source-neutral counters.

`BaseConnector.sync()` uses `finally` to guarantee disconnection after successful
or failed validation, fetch, or import operations.

## Connectors

| Connector | Current state | Import Center profile |
|---|---|---|
| `ExcelConnector` | Ready; `.xlsx` and `.csv` transport | CRM Import |
| `SchoolInfoConnector` | Mock, no writes | School Import |
| `S2BConnector` | Mock, no writes | School Market Import |
| `G2BConnector` | Mock, no writes | NaraJangteo Import |
| `EducationConnector` | Mock, no writes | Education Office Import |

The mock connectors accept deterministic records for tests and return `MOCK`
results with zero imported rows. They never import database or business-service
modules.

## Registration and UI routing

`connectors.connector_catalog()` supplies stable connector metadata to Data
Source Manager. The manager routes `metadata.profile_key` to the existing Sprint
23 Import Wizard, preserving templates, automatic column mapping, validation,
failed-row export, history, and drag-and-drop behavior.

Adding a future source requires a new `BaseConnector` implementation and one
registry entry. Data Source Manager does not require a source-specific button or
business-service import.

## Activating a remote connector

Replace the mock's transport methods while retaining these boundaries:

- credentials and HTTP sessions belong in `connect()` and `disconnect()`;
- API payload conversion belongs in `fetch()`;
- persistence must be supplied as an injected callable to `import_data()`;
- do not import database modules from the connector package;
- add lifecycle, error cleanup, payload mapping, and retry tests before enabling it.
