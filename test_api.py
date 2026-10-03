import os

import httpx
import pytest

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
TIMEOUT = 30.0

pytestmark = pytest.mark.asyncio


async def _client():
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)


async def test_home_returns_ok():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = await client.get("/")
    assert r.status_code == 200


async def test_search_returns_list():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = await client.get("/documents/search", params={"query": "машина"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_search_respects_limit_20():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = await client.get("/documents/search", params={"query": "машина"})
    assert r.status_code == 200
    assert len(r.json()) <= 20


async def test_search_empty_query_returns_422():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = await client.get("/documents/search", params={"query": ""})
    assert r.status_code == 422


async def test_search_no_matches_returns_empty_list():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = await client.get(
            "/documents/search",
            params={"query": "зззщщщъъъыыыннеекксс"},
        )
    assert r.status_code == 200
    assert r.json() == []


async def test_search_sorted_by_created_date_desc():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = await client.get("/documents/search", params={"query": "машина"})
    items = r.json()
    if len(items) < 2:
        pytest.skip("Недостаточно документов для проверки сортировки")

    dates = [item["created_date"] for item in items]
    assert dates == sorted(dates, reverse=True)


async def test_delete_nonexistent_returns_404():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = await client.delete("/documents/99999999")
    assert r.status_code == 404


async def test_delete_existing_then_404():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = await client.get("/documents/search", params={"query": "машина"})
        items = r.json()
        if not items:
            pytest.skip("Нет документов для удаления")

        doc_id = items[0]["id"]

        r1 = await client.delete(f"/documents/{doc_id}")
        assert r1.status_code == 204

        r2 = await client.delete(f"/documents/{doc_id}")
        assert r2.status_code == 404


async def test_delete_removes_from_search():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        r = await client.get("/documents/search", params={"query": "машина"})
        items = r.json()
        if not items:
            pytest.skip("Нет документов для удаления")

        doc_id = items[0]["id"]

        r1 = await client.delete(f"/documents/{doc_id}")
        assert r1.status_code == 204

        r2 = await client.get("/documents/search", params={"query": "машина"})
        remaining = [item for item in r2.json() if item["id"] == doc_id]
        assert remaining == []