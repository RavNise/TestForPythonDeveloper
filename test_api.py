import json
import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from fastapi.testclient import TestClient

import main


@pytest.fixture
def setup_test(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    index_name = f"test-documents-{uuid4().hex}"

    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(main, "INDEX_NAME", index_name)

    documents = []

    for document_id in range(1, 26):
        created_date = (
            datetime(2026, 1, 1) + timedelta(days=document_id)
        ).isoformat()

        documents.append({
            "id": document_id,
            "rubrics": ["Тест"],
            "text": "Тестовый конкурс",
            "created_date": created_date,
        })

    with sqlite3.connect(db_path) as connection:
        connection.execute("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                rubrics TEXT NOT NULL,
                text TEXT NOT NULL,
                created_date TEXT NOT NULL
            )
        """)

        connection.executemany(
            "INSERT INTO documents VALUES (?, ?, ?, ?)",
            [
                (
                    doc["id"],
                    json.dumps(doc["rubrics"], ensure_ascii=False),
                    doc["text"],
                    doc["created_date"],
                )
                for doc in documents
            ],
        )

    with Elasticsearch(main.ES_URL) as es:
        es.indices.create(
            index=index_name,
            settings={
                "number_of_shards": 1,
                "number_of_replicas": 0,
            },
            mappings={
                "dynamic": "strict",
                "properties": {
                    "id": {"type": "integer"},
                    "text": {
                        "type": "text",
                        "analyzer": "russian",
                    },
                },
            },
        )

        try:
            bulk(
                es,
                [
                    {
                        "_index": index_name,
                        "_id": str(doc["id"]),
                        "_source": {
                            "id": doc["id"],
                            "text": doc["text"],
                        },
                    }
                    for doc in documents
                ],
                refresh=True,
            )

            with TestClient(main.app) as client:
                yield client, db_path, es, index_name
        finally:
            es.indices.delete(index=index_name)


def test_search_returns_newest_20(setup_test):
    client, _, _, _ = setup_test

    response = client.get(
        "/documents/search",
        params={"query": "конкурс"},
    )

    assert response.status_code == 200
    documents = response.json()

    assert len(documents) == 20
    assert [doc["id"] for doc in documents] == list(
        range(25, 5, -1)
    )

    first = documents[0]
    assert set(first) == {"id", "rubrics", "text", "created_date"}
    assert first["rubrics"] == ["Тест"]
    assert first["text"] == "Тестовый конкурс"
    assert datetime.fromisoformat(first["created_date"]) == (
        datetime(2026, 1, 26)
    )


def test_search_without_matches(setup_test):
    client, _, _, _ = setup_test

    response = client.get(
        "/documents/search",
        params={"query": "несуществующийтермин"},
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("query", ["", "   "])
def test_search_empty_query(setup_test, query):
    client, _, _, _ = setup_test

    response = client.get(
        "/documents/search",
        params={"query": query},
    )

    assert response.status_code == 422


def test_delete_from_database_and_index(setup_test):
    client, db_path, es, index_name = setup_test

    response = client.delete("/documents/25")

    assert response.status_code == 204
    assert response.content == b""

    with sqlite3.connect(db_path) as connection:
        document = connection.execute(
            "SELECT id FROM documents WHERE id = ?",
            (25,),
        ).fetchone()

    assert document is None
    assert not es.exists(index=index_name, id="25")

    response = client.get(
        "/documents/search",
        params={"query": "конкурс"},
    )

    assert response.status_code == 200
    assert 25 not in [doc["id"] for doc in response.json()]

    assert client.delete("/documents/25").status_code == 404


def test_delete_nonexistent_document(setup_test):
    client, _, _, _ = setup_test

    response = client.delete("/documents/999999")

    assert response.status_code == 404
