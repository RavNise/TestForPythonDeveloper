import json
from pathlib import Path

from main import app


def export_docs():
    output_path = Path(__file__).resolve().parent / "docs.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            app.openapi(),
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Документация сохранена: {output_path}")


if __name__ == "__main__":
    export_docs()