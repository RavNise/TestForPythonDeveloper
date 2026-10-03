# Поисковик по документам

Простой поисковик по текстам документов: FastAPI + Elasticsearch 8 + SQLite + Docker.

## Стек

- Python 3.13
- FastAPI + Uvicorn (async)
- Elasticsearch 8.19 (в Docker)
- SQLite (через `aiosqlite`)
- Docker Compose

## Требования

- Docker Desktop (Windows / macOS / Linux)
- Файл `posts.csv` в корне проекта (исходные данные)

## Запуск

1. Собрать и поднять контейнеры:

   ```bash
   docker compose up -d
   ```

2. Импортировать документы в БД:

   ```bash
   docker compose run --rm api python import_posts.py
   ```

   Ожидаемо: `Импорт завершён. Обработано документов: 1500`

3. Проиндексировать документы в Elasticsearch:

   ```bash
   docker compose run --rm api python index_posts.py
   ```

   Ожидаемо: `Проиндексировано документов: 1500`

4. Открыть Swagger:

   ```
   http://127.0.0.1:8000/docs
   ```

## Эндпоинты

### Поиск документов

```
GET /documents/search?query=<текст>
```

- Ищет по полю `text` в Elasticsearch (`match`, `operator=and`).
- Возвращает **первые 20** документов, отсортированных по `created_date DESC, id ASC`.
- Каждый документ содержит все поля БД: `id`, `rubrics`, `text`, `created_date`.

Пример:

```bash
curl "http://127.0.0.1:8000/documents/search?query=машина"
```

### Удаление документа

```
DELETE /documents/{document_id}
```

- Удаляет документ **из БД** и **из индекса Elasticsearch**.
- `204 No Content` — успешно.
- `404 Not Found` — документ не найден.

Пример:

```bash
curl -i -X DELETE "http://127.0.0.1:8000/documents/39"
```

## Тесты

```bash
docker compose run --rm -e API_URL=http://host.docker.internal:8000 api pytest -v test_api.py
```

Ожидаемо: `9 passed`.

## OpenAPI-спека

`docs.json` — спецификация сервиса в формате OpenAPI 3.1. Пересобрать:

```bash
docker compose run --rm api python export_docs.py
```

## Остановка

```bash
docker compose down
```

Полная очистка данных (тома ES и БД):

```bash
docker compose down -v
```

## Структура проекта

```
.
├── compose.yaml          # Docker Compose
├── Dockerfile            # образ api
├── requirements.txt      # зависимости
├── main.py               # FastAPI-приложение (эндпоинты)
├── database.py           # подключение к SQLite, схема
├── import_posts.py       # импорт posts.csv → SQLite
├── index_posts.py        # индексация SQLite → Elasticsearch
├── export_docs.py        # выгрузка OpenAPI в docs.json
├── docs.json             # OpenAPI-спека
├── test_api.py           # функциональные тесты
├── pytest.ini            # конфиг pytest
└── posts.csv             # исходные данные (1500 документов)
```
