import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(
    os.getenv("DATABASE_PATH", str(BASE_DIR / "documents.db"))
)


def create_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection = sqlite3.connect(DB_PATH)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                rubrics TEXT NOT NULL,
                text TEXT NOT NULL,
                created_date TEXT NOT NULL
            )
        """)

        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    create_database()
    print("База данных готова")