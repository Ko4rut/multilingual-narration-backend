# Multilingual Automatic Narration Backend

FastAPI, SQLAlchemy, Alembic, and PostgreSQL backend for multilingual narration at points of interest.

## Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- PostgreSQL 16
- psycopg 3
- Docker Compose

## Database schema

The bootstrap migration implements the ERD using singular `snake_case` table names:

- Identity and RBAC: `action`, `management_function`, `permission`,
  `role_permission`, `role`, `manager_user`, `user_session`
- Content: `point_of_interest`, `poi_category`,
  `poi_category_mapping`, `poi_content`, `content_audio`
- Catalog and activity: `region`, `language`, `listening_history`
- Offline and audit: `offline_package`, `offline_package_item`, `audit_log`

The ERD label `content_vesion` is normalized to `content_version`, matching
`offline_package_item.content_version`. Coordinates and radius use `NUMERIC`;
timestamps are timezone-aware; audit snapshots use PostgreSQL `JSONB`.

Revision `0002_align_identifier_types` upgrades existing databases in place:
business identifiers and their foreign keys become `VARCHAR(50)`. Only audit-log
primary keys and listening installation IDs remain PostgreSQL `UUID`. Existing
numeric IDs are converted to the documented prefixes and date formats. Because
new string/UUID identifiers cannot be mapped safely back to the old integer
sequences, this revision intentionally has no destructive downgrade.

Revision `0003_update_identity_models` adds descriptions to roles and management
functions, adds nullable role creator/updater references, allows a nullable role
update timestamp, and removes the unique constraint on permission function/action
pairs.

Revision `0004_enforce_identity_constraints` converts manager-user status to the
PostgreSQL enum `manager_user_status` with `ACTIVE`/`INACTIVE` values, enforces
session timestamp invariants, and adds indexes for session expiration and
role-permission lookups.

## Docker setup

Copy the non-secret development defaults and start the complete stack:

```bash
cp .env.example .env
docker compose up --build -d
```

Compose starts the services in dependency order:

1. `postgres` becomes healthy.
2. `migrate` upgrades the schema, checks ORM/migration drift, and runs the
   idempotent seed.
3. `api` starts only after migration and seed succeed.

Default endpoints:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- PostgreSQL host port: `5433`

Useful commands:

```bash
docker compose ps
docker compose logs migrate
docker compose logs api
docker compose down
```

The application image runs as an unprivileged user. Its build context excludes
local environments, Git data, caches, logs, and `.env`.

## Local setup

This checkout uses the existing `venv` directory:

```powershell
Copy-Item .env.example .env
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m scripts.seed
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The default local `DATABASE_URL` uses PostgreSQL on host port `5433`. Inside
Docker, services connect to `postgres:5432`. Docker Compose also forwards the
Identity token/cookie settings from `.env`; without JWT key material the service
starts, but authentication endpoints return `503`.

Schema changes are applied explicitly with Alembic and are never run at API startup.

## Sample data

The seed is deterministic and idempotent. It creates a deliberately varied dataset:

- 7 actions, 5 management functions, 3 roles, and 21 permissions
- 4 manager users and 3 sessions, including inactive and revoked examples
- 5 languages, 6 regions, and 6 POI categories
- 12 POIs spread across Hà Nội, Ninh Bình, Huế, Đà Nẵng, Hồ Chí Minh City,
  and Cần Thơ
- 37 narration records covering published and draft versions
- 36 audio records split between pre-generated and TTS-generated sources
- 36 listening records across GPS, QR-code, and manual triggers
- 6 offline packages with package items and published/building states
- 5 representative audit records

Seed URLs use the reserved `example.local` domain and are metadata only. Password
and refresh-token values are non-production placeholders; they are not valid
credentials for the authentication endpoints.

Run the seed again to verify idempotency:

```powershell
.\venv\Scripts\python.exe -m scripts.seed
```

Useful checks:

```sql
SELECT COUNT(*) FROM point_of_interest;
SELECT COUNT(*) FROM poi_content;
SELECT COUNT(*) FROM content_audio;
SELECT COUNT(*) FROM listening_history;
SELECT COUNT(*) FROM offline_package_item;

SELECT r.region_code, COUNT(p.id) AS poi_count
FROM region r
LEFT JOIN point_of_interest p ON p.region_id = r.id
GROUP BY r.region_code
ORDER BY r.region_code;

SELECT l.language_code, pc.content_status, COUNT(pc.id) AS content_count
FROM language l
LEFT JOIN poi_content pc ON pc.language_id = l.id
GROUP BY l.language_code, pc.content_status
ORDER BY l.language_code, pc.content_status;
```

## API and domain architecture

```text
app/
  main.py                 FastAPI application factory and exception handlers
  core/                   Configuration, database infrastructure, exceptions
  route/                  Versioned router composition and dependencies
  domains/
    identity/             Manager users, sessions, roles and permissions
    catalog/              POI categories, regions and languages
    poi/                  POIs, category mappings, multilingual content and audio
    listening/            Listening history
    offline/              Offline packages and package items
    audit/                Administrative audit log
  models.py               ORM registry for Alembic
  db.py                   Compatibility facade for migrations and seed
```

Each domain keeps one shared router and service named after the domain, under
`routers/<domain>.py` and `services/<domain>.py`. Its `models/`, `schemas/`, and
`repositories/` packages contain one module per database table. A domain may use
`utils/<domain>.py` for small domain-specific helpers that do not belong to the
HTTP, persistence, or security layers; repository modules without an implemented
use case remain placeholders. The Identity layout and dependency rules are
documented in [app/domains/identity/README.md](app/domains/identity/README.md).

Implemented HTTP endpoints:

- `GET /health`
- `GET /api/v1/pois?offset=0&limit=20`
- `GET /api/v1/pois/{poi_id}` where `poi_id` is a string such as
  `poi-010926-951c03a1`
- `POST /api/v1/identity/login`
- `POST /api/v1/identity/refresh`
- `POST /api/v1/identity/logout`
- `GET /api/v1/identity/me`

POI reads return only records with `poi_status = 'active'`. The Identity endpoints
use Argon2id passwords, RS256 Access Tokens and opaque Refresh Tokens stored in an
`HttpOnly` cookie. Refresh Tokens are stored only as SHA-256 hashes and rotated
under a row lock without extending the session's absolute expiration. A deployment
must supply `JWT_PRIVATE_KEY` and `JWT_PUBLIC_KEYS`; no development signing key is
built into the application. The API can start without those keys, but Identity
endpoints that construct the JWT provider return `503 Service Unavailable` until
valid keys are supplied. Administrative Identity endpoints, nearby search, QR
activation, narration selection, TTS, listening ingestion, and offline package
generation remain future use cases.

The target login, JWT, refresh-token, password-hashing, key-management, and
revocation contracts are documented in
[docs/authentication-design.md](docs/authentication-design.md). The document
also identifies production key provisioning and future authentication hardening.

## Verification

```powershell
.\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
.\venv\Scripts\python.exe -m alembic check
docker compose config --quiet
```

`alembic check` requires the configured database to be upgraded to `head`.
Integration checks that change schema or data must use an isolated test database,
not a populated development database.

## Agent instructions

Repository conventions are documented in [AGENTS.md](AGENTS.md). Backend work must
also follow [skills/mnr-backend/SKILL.md](skills/mnr-backend/SKILL.md).
