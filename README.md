# Comicly Backend v2

Illustrative reader: upload a book → per-page AI illustrations with **locked visual style + consistent characters** across the whole book.

Pipeline per page: `reader → director → artist → memory` (`app/graph/pipeline.py`).

## Quickstart (local)

```bash
cp .env.example .env   # then set a fresh GOOGLE_API_KEY (the old committed key is revoked/invalid)
docker compose up -d postgres redis minio
uv sync --all-extras
uv run alembic upgrade head
uv run uvicorn app.main:app --port 8000      # API
uv run arq app.workers.tasks.WorkerSettings  # worker (separate terminal)
```

Dev without a Gemini key: set `MOCK_GENERATION=true` in `.env` — deterministic placeholder frames, same API contract.

## API (v1)

- `POST /api/v1/books/upload` (multipart: `file`, `title`, `author`) → `{book_id, total_pages}` — PDF/EPUB/TXT
- `GET /api/v1/books` / `GET /api/v1/books/{id}`
- `GET /api/v1/books/{id}/pages?page=&size=` / `GET .../pages/{n}`
- `POST /api/v1/books/{id}/generate {"page_no":1,"force":false}` → `202 {job_id}` (`style_override` only on page 1 — style locks after)
- `GET /api/v1/jobs/{job_id}` + `GET /api/v1/jobs/{job_id}/stream` (SSE: queued→reading→directing→rendering→saving→done/error)
- `GET /api/v1/books/{id}/frames/{n}` (image_url + agent outputs), `GET .../characters`, `GET .../frames`
- Auth: `POST /api/v1/auth/signup`, `POST /api/v1/auth/login` → JWT, `GET /api/v1/auth/me`. Everything else needs `Authorization: Bearer <token>`; books are private per user (other users' ids return 404). The SSE stream also accepts `?token=` since EventSource can't set headers.
- `GET /health`, `GET /ready`

Claim pre-auth orphan books: `uv run python scripts/claim_books.py --email you@example.com`.

Legacy `POST /api/upload`, `POST /api/generate` still mounted for the old frontend.

## Consistency design

- `style_lock` frozen on page 1 (art_style, lighting, palette, realism, seed_anchor, rendering_mode)
- Character sheet per book (`appearance` + `visual_anchors`) injected into **every** image prompt; reference portraits + previous frame passed as image inputs
- Deterministic seed `(anchor*7919 + page*104729) % 2e9`
- Memory snapshot per page (story, relationships, character deltas)

## Tests / lint

```bash
uv run pytest -q
uv run ruff check app/ tests/
```

## Security notes

- Never commit `.env`. The key once committed in git history must be revoked in Google AI Studio.
- CORS is locked to `FRONTEND_URL` (no more `*` + credentials).
