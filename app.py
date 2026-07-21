from core.logger import configure_logging
from gui.main_window import run
from services.database import create_database

configure_logging()
create_database()

if __name__ == "__main__":
    run()
