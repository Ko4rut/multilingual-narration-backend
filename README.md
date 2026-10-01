# Multilingual Automatic Narration Backend

Database foundation for the Multilingual Automatic Narration System. The supplied use cases cover GPS/geofence-driven multilingual narration, QR activation, content administration with TTS/pre-generated audio, POI management, and optional offline packages.

## Stack
- Python 3.12+
- SQLAlchemy 2.x
- Alembic
- PostgreSQL 16
- psycopg 3
- Docker Compose

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

## Project structure
```text
app/                    SQLAlchemy base and models
alembic/                migration environment and revisions
scripts/seed.py         idempotent development seed
scripts/wait_for_postgres.sh
Dockerfile
docker-compose.yml
.env.example
requirements.txt
```

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
