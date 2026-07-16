from gui.main_window import run
from services.database import create_database

create_database()

if __name__ == "__main__":
    run()