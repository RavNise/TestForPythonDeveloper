import asyncio
import os

import aiosqlite
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from database import DB_PATH


ES_URL = os.getenv(
    "ELASTICSEARCH_URL",
    "http://127.0.0.1:9200",
)
INDEX_NAME = "documents"


async def index_posts():
    if not DB_PATH.exists():
        raise FileNotFoundError("Сначала создай базу и загрузи posts.csv")

    async with aiosqlite.connect(DB_PATH) as connection:
        async with connection.execute(
            "SELECT id, text FROM documents"
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        print("База пустая. Сначала запусти import_posts.py")
        return

    async with AsyncElasticsearch(
        ES_URL,
        request_timeout=30,
    ) as client:
        if not await client.indices.exists(index=INDEX_NAME):
            await client.indices.create(
                index=INDEX_NAME,
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

        actions = [
            {
                "_index": INDEX_NAME,
                "_id": str(document_id),
                "_source": {
                    "id": document_id,
                    "text": text,
                },
            }
            for document_id, text in rows
        ]

        success_count, _ = await async_bulk(
            client,
            actions,
            chunk_size=500,
        )

        await client.indices.refresh(index=INDEX_NAME)

        print(f"Проиндексировано документов: {success_count}")


if __name__ == "__main__":
    asyncio.run(index_posts())