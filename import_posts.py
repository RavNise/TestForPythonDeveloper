import ast
import csv
import json
import sqlite3
from datetime import datetime

from database import BASE_DIR, DB_PATH, create_database


def import_posts():
    create_database()

    csv_path = BASE_DIR / "posts.csv"
    connection = sqlite3.connect(DB_PATH)
    count = 0

    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for document_id, row in enumerate(reader, start=1):
                rubrics = ast.literal_eval(row["rubrics"])

                if not isinstance(rubrics, list) or not all(
                    isinstance(rubric, str) for rubric in rubrics
                ):
                    raise ValueError(
                        f"Некорректные рубрики у документа {document_id}"
                    )

                created_date = datetime.fromisoformat(
                    row["created_date"]
                ).isoformat()

                connection.execute(
                    """
                    INSERT INTO documents (id, rubrics, text, created_date)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        rubrics = excluded.rubrics,
                        text = excluded.text,
                        created_date = excluded.created_date
                    """,
                    (
                        document_id,
                        json.dumps(rubrics, ensure_ascii=False),
                        row["text"],
                        created_date,
                    ),
                )

                count += 1

        connection.commit()
        print(f"Импорт завершён. Обработано документов: {count}")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    import_posts()