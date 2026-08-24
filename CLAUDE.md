# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

```
backend/    FastAPI application (Python 3.12, uv)
frontend/   React 18 + TypeScript + Vite SPA
configs/    Runtime storage for uploaded config files (gitignored)
```

## Backend

### Common commands (run from `backend/`)

```bash
uv sync --dev                        # install / refresh all dependencies
uv run pytest                        # run full test suite (enforces 90% coverage)
uv run pytest tests/test_auth.py     # run a single test file
uv run pytest -k "test_login"        # run tests matching a pattern
uv run pytest --no-cov               # skip coverage (faster)
uv run uvicorn app.main:app --reload # start dev server on :8000
uv run alembic revision --autogenerate -m "description"  # create migration
uv run alembic upgrade head          # apply migrations manually
```

All pytest and coverage settings live in `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]`). The coverage `core = sysmon` setting is required — without it, coverage.py's `sys.settrace` misses lines after `await` points in async route handlers on Python 3.12.

### Architecture

The app is a standard FastAPI application with these layers:

**`app/config.py`** — single `Settings` object (pydantic-settings, reads `.env`). Cached with `@lru_cache`. All other modules call `get_settings()`.

**`app/database.py`** — async SQLAlchemy engine + `AsyncSessionLocal` session maker + `Base` declarative base. `get_db()` here is the real dependency; `app/api/deps.py` has an identical copy (FastAPI dependency injection requires it to be importable from there). Tests override `get_db` via `app.dependency_overrides`.

**`app/models/`** — two models:
- `User` — id (UUID string), username, email, hashed_password, is_admin, is_active
- `Configuration` + `Revision` — a config has many revisions (append-only). `Revision` stores the file path, not the content. `revision_number` is sequential per config.

**`app/api/deps.py`** — three dependency chain: `get_db` → `get_current_user` → `get_current_active_user` → `require_admin`. Routes import the appropriate level.

**`app/api/routes/`** — three routers, all mounted under `/api`:
- `auth.py` — `/auth/*` — register, login, refresh, logout, me. Login accepts username or email. First registered user is auto-promoted to admin. Refresh tokens are httpOnly cookies at path `/api/auth`; access tokens are bearer tokens in memory only.
- `configurations.py` — `/configurations/*` — CRUD for configs, revision upload, content fetch, diff between any two revisions.
- `admin.py` — `/admin/*` — admin-only user management and config management.

**`app/core/security.py`** — bcrypt directly (not passlib — passlib is incompatible with bcrypt 5.x). JWT via python-jose. Tokens carry a `type` claim (`"access"` or `"refresh"`) so they can't be substituted for each other.

**`app/core/betaflight.py`** — stateless parser. `parse_betaflight_config()` returns a `BetaflightConfig` dataclass or `None` if the file isn't a valid Betaflight CLI dump. Validation requires the `# Betaflight` version header plus either `batch start` or `board_name`.

**`app/services/storage.py`** — file storage. Config files are gzip-compressed and stored in a two-level UUID prefix tree: `configs/{uuid[:2]}/{uuid[2:4]}/{config_uuid}/{revision_uuid}.txt.gz`. All load/delete operations resolve the full path and verify it stays within the base directory before operating (path traversal protection). `_get_configs_base()` is a module-level function so tests can patch it via `unittest.mock.patch("app.services.storage._get_configs_base", return_value=tmp_path)`.

**`app/main.py`** — lifespan runs Alembic migrations via `asyncio.to_thread()` because `alembic.command.upgrade()` internally calls `asyncio.run()`, which fails inside an already-running event loop.

### Adding a migration

After changing a model, run:
```bash
uv run alembic revision --autogenerate -m "short description"
```
Review the generated file in `alembic/versions/` before applying.

### Test fixtures (`tests/conftest.py`)

- `test_engine` — per-test in-memory SQLite, schema created via `Base.metadata.create_all`
- `db_session` — raw session for direct DB setup in tests
- `client` — `httpx.AsyncClient` wired to the app with DB override, storage redirected to `tmp_path`, Alembic patched out
- `make_user(session, ...)` — async helper to insert a user
- `auth_headers(user_id)` — returns `{"Authorization": "Bearer <token>"}`
- `upload_config(client, headers, ...)` — posts a config file, asserts 201

`EXAMPLE_CONFIG` in conftest is a minimal but complete Betaflight config string that passes the parser's validation.

### Key constraints

- `max_upload_size` in `Settings` is currently **64 KB** — configs are plain text so this is intentional.
- `allowed_origins` in `.env` must be a JSON array: `["http://localhost:5173"]`
- Rate limits: 10/min on register, 20/min on login (slowapi).

## Frontend

### Common commands (run from `frontend/`)

```bash
npm install          # install dependencies
npm run dev          # dev server on :5173
npm run build        # TypeScript check + Vite production build
npm run preview      # preview production build
```

### Architecture

React SPA with React Router v6, TanStack Query for server state, Axios for HTTP. Tailwind CSS with a dark/orange theme.

- `src/contexts/AuthContext.tsx` — global auth state (access token in memory, user object). Provides `login`, `logout`, `register` actions.
- `src/api/client.ts` — Axios instance pointing at `http://localhost:8000`. Attaches the bearer token from `AuthContext` and sends credentials (for refresh cookie).
- `src/api/types.ts` — TypeScript interfaces mirroring the backend Pydantic schemas.
- Pages: `Login`, `Register`, `Dashboard` (config list), `ConfigurationDetail` (revisions + upload), `DiffView` (side-by-side diff via diff2html).
- `src/pages/admin/` — admin section with user and config management tables.

## Docker

```bash
docker compose up --build    # start backend (:8000) + frontend (:3000)
```

The backend Dockerfile installs the uv binary, runs `uv sync --no-dev --frozen`, and starts uvicorn from `.venv/bin/uvicorn`. The frontend Dockerfile builds the Vite SPA and serves it with Nginx.
