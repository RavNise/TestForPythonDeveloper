from elasticsearch import NotFoundError
from fastapi import Path, Response
import json
from contextlib import asynccontextmanager
from datetime import datetime

import aiosqlite
from elastic_transport import TransportError
from elasticsearch import AsyncElasticsearch, ApiError
from elasticsearch.helpers import async_scan
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from database import DB_PATH
from index_posts import ES_URL, INDEX_NAME


class Document(BaseModel):
    id: int
    rubrics: list[str]
    text: str
    created_date: datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncElasticsearch(
        ES_URL,
        request_timeout=30,
    ) as client:
        app.state.es = client
        yield


app = FastAPI(
    title="Поиск документов",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def home():
    return {"message": "Поисковик работает"}


@app.get("/documents/search", response_model=list[Document])
async def search_documents(
    request: Request,
    query: str = Query(min_length=1, max_length=4096),
):
    query = query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Введите непустой поисковый запрос",
        )

    document_ids = []

    try:
        async for hit in async_scan(
            client=request.app.state.es,
            index=INDEX_NAME,
            query={
                "query": {
                    "match": {
                        "text": {
                            "query": query,
                            "operator": "and",
                        }
                    }
                },
                "_source": ["id"],
            },
            size=500,
        ):
            document_ids.append(hit["_source"]["id"])

    except (ApiError, TransportError) as error:
        raise HTTPException(
            status_code=503,
            detail="Поисковый сервер недоступен или индекс не готов",
        ) from error

    if not document_ids:
        return []

    placeholders = ",".join("?" for _ in document_ids)

    sql = f"""
        SELECT id, rubrics, text, created_date
        FROM documents
        WHERE id IN ({placeholders})
        ORDER BY created_date DESC, id ASC
        LIMIT 20
    """

    async with aiosqlite.connect(DB_PATH) as connection:
        connection.row_factory = aiosqlite.Row
        async with connection.execute(sql, document_ids) as cursor:
            rows = await cursor.fetchall()

    return [
        Document(
            id=row["id"],
            rubrics=json.loads(row["rubrics"]),
            text=row["text"],
            created_date=row["created_date"],
        )
        for row in rows
    ]

    
@app.delete(
    "/documents/{document_id}",
    status_code=204,
    response_class=Response,
)
async def delete_document(
    request: Request,
    document_id: int = Path(gt=0),
):
    async with aiosqlite.connect(DB_PATH, timeout=30) as connection:
        await connection.execute("BEGIN IMMEDIATE")

        async with connection.execute(
            "SELECT id FROM documents WHERE id = ?",
            (document_id,),
        ) as cursor:
            document = await cursor.fetchone()

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Документ не найден",
            )

        try:
            await request.app.state.es.delete(
                index=INDEX_NAME,
                id=str(document_id),
                refresh="wait_for",
            )

        except NotFoundError:
            # документа в индексе нет — это нормально, продолжаем удалять из БД
            pass

        except (ApiError, TransportError) as error:
            raise HTTPException(
                status_code=503,
                detail="Не удалось подтвердить удаление из индекса. "
                       "Повторите запрос",
            ) from error

        await connection.execute(
            "DELETE FROM documents WHERE id = ?",
            (document_id,),
        )
        await connection.commit()

    return Response(status_code=204)