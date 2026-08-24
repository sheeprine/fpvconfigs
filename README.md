# FPV Configs

A self-hosted web application for storing, versioning, and diffing Betaflight flight controller configuration backups. Upload CLI dump files, track changes across firmware updates, and compare revisions side-by-side.

## Features

- **Config versioning** — upload multiple revisions of the same config and diff any two against each other
- **Metadata extraction** — automatically parses Betaflight version, MSP API, config revision, board name, manufacturer ID, craft name, and pilot name from the CLI dump header
- **User isolation** — each user sees only their own configs
- **Admin panel** — manage users (create, update, set password, delete) and all configurations
- **Secure by default** — bcrypt passwords, short-lived JWT access tokens + httpOnly refresh cookies, rate limiting, security headers, path traversal protection on file storage
- **First user is admin** — no separate bootstrap step needed

## Quick start (Docker)

```bash
git clone <repo>
cd fpvconfigs

# Generate a secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Create the backend env file
cp backend/.env.example backend/.env
# Edit backend/.env and set SECRET_KEY to the value above

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/api/docs

## Manual setup

### Backend

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
cp .env.example .env          # edit SECRET_KEY at minimum
uv sync --dev                 # install dependencies + create .venv
uv run uvicorn app.main:app --reload
```

The app runs on http://localhost:8000. Alembic migrations run automatically on startup.

### Frontend

Requires Node.js 18+.

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on http://localhost:5173 and proxies API calls to `http://localhost:8000`.

## Configuration

All backend settings are read from `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | *(insecure default)* | 256-bit hex string for JWT signing — **must be changed in production** |
| `DATABASE_URL` | `sqlite+aiosqlite:///./fpvconfigs.db` | SQLAlchemy async database URL |
| `CONFIGS_DIR` | `../configs` | Directory where compressed config files are stored |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh cookie lifetime |
| `ALLOWED_ORIGINS` | `["http://localhost:5173"]` | CORS origins — must be a JSON array |
| `MAX_UPLOAD_SIZE` | `65536` | Maximum config file size in bytes (64 KB) |

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## File storage

Configs are stored gzip-compressed in a two-level UUID prefix tree to avoid large flat directories:

```
configs/
└── {uuid[0:2]}/
    └── {uuid[2:4]}/
        └── {config_uuid}/
            ├── {revision_uuid}.txt.gz
            └── {revision_uuid}.txt.gz
```

## API reference

Full interactive docs are available at `/api/docs` when the backend is running.

### Auth — `/api/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/register` | — | Create account; first user becomes admin |
| `POST` | `/login` | — | Login with username or email |
| `POST` | `/refresh` | cookie | Exchange refresh cookie for new access token |
| `POST` | `/logout` | — | Clear refresh cookie |
| `GET` | `/me` | bearer | Return current user |

### Configurations — `/api/configurations`

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | List all configs for the current user |
| `POST` | `/` | Upload a new config (multipart `file` field) |
| `GET` | `/{id}` | Get config detail with all revisions |
| `DELETE` | `/{id}` | Delete config and all its files |
| `POST` | `/{id}/revisions` | Upload a new revision |
| `GET` | `/{id}/revisions/{rev_id}/content` | Download raw revision text |
| `GET` | `/{id}/diff/{rev1_id}/{rev2_id}` | Unified diff between two revisions |

All configuration endpoints require a valid bearer token.

### Admin — `/api/admin` *(admin only)*

| Method | Path | Description |
|---|---|---|
| `GET` | `/users` | List users (paginated, `?skip=&limit=`) |
| `POST` | `/users` | Create user |
| `GET` | `/users/{id}` | Get user |
| `PUT` | `/users/{id}` | Update user fields (username, email, password, is_active, is_admin) |
| `DELETE` | `/users/{id}` | Delete user |
| `GET` | `/configurations` | List all configs (filter by `?user_id=&search=`) |
| `DELETE` | `/configurations/{id}` | Delete any config |
| `DELETE` | `/configurations/{id}/revisions/{rev_id}` | Delete a single revision (last revision is protected) |

## Development

```bash
cd backend
uv run pytest                        # full suite with coverage (90% minimum enforced)
uv run pytest tests/test_auth.py     # single file
uv run pytest -k "test_login"        # filter by name
uv run pytest --no-cov               # skip coverage for speed

# After modifying a model:
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

```bash
cd frontend
npm run build    # TypeScript check + production build
```

## Tech stack

**Backend** — Python 3.12, FastAPI 0.115, SQLAlchemy 2 (async), Alembic, aiosqlite, bcrypt, python-jose, slowapi, uv

**Frontend** — React 18, TypeScript, Vite, TailwindCSS, TanStack Query, Axios, diff2html
