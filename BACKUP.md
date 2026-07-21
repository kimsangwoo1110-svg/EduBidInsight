# Backup and Restore

## Automatic backup

EduBid Insight creates a verified SQLite backup during normal application exit. The newest seven `edubid_*.db` files are retained; older managed backups are removed automatically.

Closing the application through forced process termination or an operating-system crash may prevent the exit backup. Use manual backups before high-risk operations.

## Manual backup

1. Open Settings → Backup.
2. Confirm the backup directory.
3. Select **Create Backup**.
4. Verify that the new file appears in the backup list.

SQLite's online backup API creates a transactionally consistent copy. Both the source and destination must pass `PRAGMA integrity_check`.

## Restore

1. Close other EduBid Insight windows or processes.
2. Open Settings → Backup → **Restore Backup**.
3. Select an `edubid_*.db` file.
4. Confirm replacement of the active database.
5. Restart EduBid Insight.

Restore writes to a temporary database, verifies integrity, and only then atomically replaces the active database. An invalid backup is rejected without changing the active database.

## Default locations

- Portable mode: `backups/` beside the application.
- Installed mode: `%LOCALAPPDATA%/EduBidInsight/backups` on Windows.

The location can be changed under Settings → Backup. Keep an additional copy on separate storage for disaster recovery.
