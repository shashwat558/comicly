import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models.book import Book
from app.models.user import User


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def signup(client: AsyncClient, email: str, password: str = "password123"):
    r = await client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


async def login(client: AsyncClient, email: str, password: str = "password123") -> str:
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_protected_routes_need_token(client: AsyncClient):
    assert (await client.get("/api/v1/books")).status_code == 401
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_signup_duplicate_and_bad_login(client: AsyncClient):
    email = f"u-{uuid.uuid4().hex[:8]}@example.com"
    await signup(client, email)
    r = await client.post("/api/v1/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 409
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpass1"})
    assert r.status_code == 401
    r = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert r.status_code == 401


async def test_me_and_isolation(client: AsyncClient):
    a_email = f"a-{uuid.uuid4().hex[:8]}@example.com"
    b_email = f"b-{uuid.uuid4().hex[:8]}@example.com"
    await signup(client, a_email)
    await signup(client, b_email)
    a_tok, b_tok = await login(client, a_email), await login(client, b_email)

    me = await client.get("/api/v1/auth/me", headers=auth(a_tok))
    assert me.status_code == 200 and me.json()["email"] == a_email

    # a uploads a book
    r = await client.post(
        "/api/v1/books/upload",
        headers=auth(a_tok),
        files={"file": ("t.txt", b"Case walked into the neon Chat. " * 20, "text/plain")},
        data={"title": "Private Book", "author": "Anon"},
    )
    assert r.status_code == 201, r.text
    book_id = r.json()["id"]

    # b sees an empty library and gets 404 on a's book (no id leak)
    assert (await client.get("/api/v1/books", headers=auth(b_tok))).json() == []
    assert (await client.get(f"/api/v1/books/{book_id}", headers=auth(b_tok))).status_code == 404
    assert (await client.get(f"/api/v1/books/{book_id}/pages", headers=auth(b_tok))).status_code == 404
    r = await client.post(
        f"/api/v1/books/{book_id}/generate",
        headers=auth(b_tok),
        json={"page_no": 1},
    )
    assert r.status_code == 404

    # a can still see it
    assert (await client.get(f"/api/v1/books/{book_id}", headers=auth(a_tok))).status_code == 200

    # cleanup so dev db stays tidy (books cascade from users)
    async with SessionLocal() as db:
        for email in (a_email, b_email):
            u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if u is not None:
                await db.delete(u)
        await db.commit()
