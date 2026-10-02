# Multilingual Automatic Narration Backend

Database foundation for the Multilingual Automatic Narration System. The supplied use cases cover GPS/geofence-driven multilingual narration, QR activation, content administration with TTS/pre-generated audio, POI management, and optional offline packages.

## Stack
- Python 3.12+
- SQLAlchemy 2.x
- Alembic
- PostgreSQL 16
- psycopg 3
- Docker Compose

## Coding agent instructions

[AGENTS.md](AGENTS.md) defines repository rules and directs agents doing backend
work to [the MNR backend skill](skills/mnr-backend/SKILL.md). The skill describes
domain ownership, implementation steps, migration handling and meaningful checks.
It lives with this source and is loaded through AGENTS.md; it is not installed as
a global skill or guaranteed to appear in a skill picker.

Example request: "Read AGENTS.md and skills/mnr-backend/SKILL.md, then implement
the POI update use case following the existing domain architecture."

Maintain these instructions when architecture conventions change. This layout uses
the documented [AGENTS.md guidance pattern](https://developers.openai.com/cookbook/articles/codex_exec_plans)
and [SKILL.md format](https://developers.openai.com/plugins/build/skills).

## Database architecture
The ERD entities are implemented as `action`, `management_function`, `permission`, `role_permission`, `role`, `management_user`, `audit_log`, `point_of_interest`, `poi_content`, `content_audio`, `listening_history`, `poi_category`, `poi_category_mapping`, `region`, `language`, and `offline_package`.

ERD names are mapped to snake_case identifiers. The column `checksum_sha25` is preserved exactly because it is the column name shown in the ERD.

## Prerequisites
- Docker and Docker Compose for the easiest setup.
- Or Python 3.12+ and PostgreSQL 16 for local execution.

## Environment
```bash
cp .env.example .env
```
Never commit `.env`. The example contains development-only credentials; production credentials must be supplied through the deployment environment.

## Docker setup
```bash
cp .env.example .env
docker compose up --build
```
PostgreSQL is health-checked before the `db-init` service runs `alembic upgrade head` and the idempotent seed script.

Stop containers:
```bash
docker compose down
```
Reset the development database and volume:
```bash
docker compose down -v
```

## Local migrations
Install dependencies:
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```
Configure `DATABASE_URL`, then:
```bash
alembic upgrade head
python scripts/seed.py
```
Rollback and re-apply:
```bash
alembic downgrade base
alembic upgrade head
```

## Seed data
The seed is idempotent and covers all ERD tables. It includes Vietnamese (`vi`), English (`en`), and Japanese (`ja`) language records; multiple tourism regions; historical, museum, landmark, and cultural categories; four POIs; multilingual narration content; pre-generated and TTS-generated audio metadata; listening history; category mappings; offline packages; RBAC records; management users; and audit logs.

The dummy management-user password hashes are deliberately non-production placeholders. No plaintext password is stored and no real credential is included.

## Verify seeded data
Useful checks:
```sql
SELECT COUNT(*) FROM point_of_interest;
SELECT COUNT(*) FROM poi_content;
SELECT COUNT(*) FROM content_audio;
SELECT COUNT(*) FROM listening_history;
SELECT COUNT(*) FROM offline_package;
SELECT l.language_code, COUNT(pc.id)
FROM language l LEFT JOIN poi_content pc ON pc.language_id = l.id
GROUP BY l.language_code ORDER BY l.language_code;
```

Run the seed a second time and repeat the counts; stable natural keys prevent duplicate master/content/package records. Listening-history records use a stable POI/start timestamp check as well.

## Useful PostgreSQL commands
```bash
psql "$DATABASE_URL"
```
Inside `psql`:
```sql
\dt
SELECT version_num FROM alembic_version;
SELECT * FROM point_of_interest ORDER BY poi_priority;
SELECT p.poi_name, l.language_code, pc.narration_title, ca.audio_source_type
FROM point_of_interest p
JOIN poi_content pc ON pc.poi_id = p.id
JOIN language l ON l.id = pc.language_id
JOIN content_audio ca ON ca.poi_content_id = pc.id
ORDER BY p.id, l.language_code;
```

## API skeleton and domain architecture

Run the API locally (PostgreSQL must already be running):
```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
Swagger UI: http://127.0.0.1:8000/docs. `python -m app` also starts the API.
Schema changes are applied explicitly with Alembic, never at API startup.
Docker Compose currently runs PostgreSQL and the migration/seed job; run the API
locally using the command above.

```text
app/
  main.py                 FastAPI application factory and exception handlers
  core/
    config.py             Typed environment settings
    database.py           SQLAlchemy Base, engine and session infrastructure
    exceptions.py         Shared domain exceptions
  route/
    api.py                Assemble domain routers under /api/v1
    dependencies.py       Request-scoped database session
  domains/
    poi/                  POIs, categories and category mappings (UC01/02/05)
    narration/            Multilingual content and audio/TTS (UC03/04)
    catalog/              Regions and languages
    identity/             Management users, roles and permissions
    listening/            Listening history
    offline/              Optional offline packages (UC06)
    audit/                Administrative audit log
  models.py               Model registry and compatibility exports
  db.py                   Compatibility exports for existing callers
```
Each domain contains `models.py`, `schemas.py`, `router.py`, `service.py`, and
`repository.py`. The POI domain is the working reference implementation:

- `router.py` is the HTTP controller: paths, validation, dependency injection,
  response schemas. A separate pass-through controller layer is unnecessary.
- `service.py` owns business rules and write transaction boundaries.
- `repository.py` owns queries and accepts a SQLAlchemy Session; it does not commit.
- `models.py` contains ORM entities; `schemas.py` contains public request/response DTOs.
- `core` contains shared infrastructure, not business models.

Implemented: `GET /health` (liveness), `GET /api/v1/pois?offset=0&limit=20`,
`GET /api/v1/pois/{poi_id}`. POI endpoints only return active records; missing or
inactive POIs return 404. Pagination has a maximum of 100 records per request.
Other domains have model definitions and extension files only, with no endpoints yet.
Authentication/RBAC, admin CRUD, nearby search, QR activation, narration selection,
TTS, listening events, and offline generation remain future business implementation.

To add a use case, define schemas, implement repository queries and service rules,
then add the domain router endpoint. Domain routers are already registered centrally.
Use `with session.begin():` in write services to commit/rollback the whole use case;
request session cleanup rolls back any uncommitted work. Services should raise domain
exceptions and leave HTTP status mapping to the application.

The local `.env` uses port 5433 for Docker PostgreSQL. `DATABASE_URL` is the API and
Alembic connection setting; keep its port consistent with `POSTGRES_PORT` for local
execution. Inside Docker, PostgreSQL continues to listen on port 5432.

Architecture reference: [FastAPI larger applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/).

## Migration architecture
`alembic/env.py` reads `DATABASE_URL` from the environment through `app.db`. The initial revision creates parent/reference tables before dependent tables and its downgrade reverses that dependency order. Foreign-key indexes are added for frequently queried relationship fields.

## Schema assumptions
- Integer surrogate primary keys are used where the ERD shows `id` without a more specific type.
- `latitude`/`longitude` use `NUMERIC(9,6)` and `trigger_radius` uses `NUMERIC(8,2)`.
- `audio_size`, `total_size`, and `duration_sec` use integers.
- `old_values` and `new_values` use PostgreSQL `JSONB` because the ERD does not specify a type and these fields represent structured audit snapshots.
- `created_at` and publication/expiry timestamps use timezone-aware timestamps.
- Names/codes/emails/QR values that function as natural identifiers are unique to make the seed idempotent.
- The ERD does not define authentication endpoints or token semantics; therefore this database implementation does not invent an application login/JWT flow.

## Troubleshooting
- If `db-init` fails, inspect its logs: `docker compose logs db-init`.
- If PostgreSQL is unhealthy, inspect: `docker compose logs postgres`.
- If a migration fails, fix the database/configuration issue and rerun `docker compose up`.
- To start from a clean development database: `docker compose down -v && docker compose up --build`.
