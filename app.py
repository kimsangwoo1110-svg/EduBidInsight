from core.app_settings import get_app_settings
from core.logger import configure_logging, install_crash_logging
from services import database


def main():
    settings = get_app_settings()
    settings.ensure_directories()
    settings.save()
    database.configure_database(settings.database_path)
    configure_logging(settings.log_directory, force=True)
    install_crash_logging(settings.log_directory)
    from services.migration_service import MigrationService

    MigrationService(settings.database_path).migrate()
    from gui.main_window import run

    run(settings)

if __name__ == "__main__":
    main()
