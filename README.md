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

### Legacy Language status migration preparation

For an existing pre-`0005` development database that still contains
`language.language_status = 'active'`, inspect the statuses and back up the
database first. With the correct database configured, run:

```powershell
python -m scripts.seed --reconcile-language-statuses
python -m alembic upgrade head
python -m scripts.seed
```

The explicit reconciliation command converts only recognized legacy values
(`active`/`supported` → `SUPPORTED`, `unsupported` → `UNSUPPORTED`)
without creating any seed records. Unknown statuses raise an error and require
manual review. Do not use `alembic stamp head` to bypass migration checks.
Normal seeding uses the `LanguageStatus` enum, preserves existing language
statuses (including manually disabled languages), and only defaults
new records to `SUPPORTED`. Ensure these commands point to the intended
development/test database, not production.

Revision `0006_offline_contract` aligns Group 3 with the database-design
contract: one logical package per canonical filter key, nullable manifest
metadata while building, BIGINT total size, package status enum, and
package-item uniqueness by content. Migration preserves package/item IDs and
existing URLs, normalizes legacy keys and status values, and fails if
duplicate filters or content memberships require manual reconciliation.
**Previously published manifests using legacy keys/ZIP URLs must be rebuilt
and verified before being offered to mobile.** Seed URLs under
`cdn.example.local` remain placeholders, not downloadable assets.

Revision `0007_poi_schema_alignment` adds missing POI/Content/Audio constraints and
indexes required by the merged POI management models: coordinate/radius and
content status/version checks, the single PUBLISHED version per POI and
language, the single audio per content, and audio BIGINT sizing. The migration
refuses duplicate or otherwise invalid legacy data **before** schema changes
instead of dropping records. For an existing database, back up and inspect
any reported conflicting records; no volume reset is required.

The narration query compares the `LanguageStatus.SUPPORTED` enum directly
rather than applying `lower()` to a PostgreSQL enum. Language preflight uses
SQL `trim()` so SQLite-based unit tests and PostgreSQL agree.

## Docker setup

Copy development defaults and start PostgreSQL plus the one-shot migration/seed
service. The containerized API is **optional** to avoid occupying port 8000
while developing with Uvicorn from the source tree:

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps -a
docker compose logs migrate
```

By default, `postgres` is available on host port **5433** and `migrate`
waits for its healthcheck, reconciles old language statuses, runs
`alembic upgrade head`, `alembic check`, and seeds baseline data.
The `api` service is under the `api` Compose profile and is **not started**
by the default `up`.

Start the FastAPI development server in a separate shell:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

To run the **entire** stack inside Docker instead, stop the local Uvicorn
process and explicitly enable the API profile:

```bash
docker compose --profile api up --build -d
docker compose --profile api ps
```

The API is then available at http://localhost:8000 and Swagger UI at
http://localhost:8000/docs. The database is still on host port 5433.
If the API container was previously running, use `docker compose stop api`
before starting Uvicorn locally.

For a disposable development database only, `docker compose down -v`
resets volumes **and permanently destroys all saved data**. An existing
database is never pruned by the seed: old demo users, POIs and packages
will remain until explicitly reviewed and cleaned up. Do not reset a
database with valuable data.

The seed uses `SEED_ADMIN_PASSWORD` (development default: `admin123`)
only when creating `admin@mnr.com`; the password is hashed with Argon2id.
Do not use this default credential in production. Login requires actual
JWT signing and verification keys; the placeholders in `.env.example`
are not usable keys. For local HTTP cookie testing set
`AUTH_COOKIE_SECURE=false`.

Useful commands:

```bash
docker compose ps -a
docker compose logs migrate
docker compose --profile api logs api
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

`DATABASE_URL`, `JWT_ACTIVE_KEY_ID`, `JWT_ISSUER` and `JWT_AUDIENCE` are required
settings; `.env.example` provides local development values. The local database URL
uses PostgreSQL on host port `5433`; inside Docker, services connect to
`postgres:5432`. Identity login additionally requires `JWT_PRIVATE_KEY` and
`JWT_PUBLIC_KEYS`; real keys must come from the deployment secret store and must
not be committed to `.env` or source control.

Schema changes are applied explicitly with Alembic and are never run at API startup.

## Sample data

On a **fresh empty database**, the seed creates 99 records in 12 tables:

- 6 actions (no `generate_audio`), 6 management functions, 22 permissions.
- 1 `Super Administrator` role initially assigned all 22 permissions.
- 1 manager account: `admin@mnr.com`. Its bootstrap password is hashed
  with `Argon2PasswordHasher` only on account creation and is never reset
  by a later seed.
- 5 languages (vi/en/ja/fr/ko), 6 regions and 6 POI categories.
- 3 INACTIVE POIs: Văn Miếu – Quốc Tử Giám, Tràng An, and Bảo tàng Chứng
  tích Chiến tranh, each mapped to two appropriate categories.
- 15 DRAFT narration records (one per POI and language, version 1).
- No content audio, login sessions, listening history, offline packages,
  offline package items or audit logs. These records arise from actual use.

POI image URLs at `cdn.example.local` remain placeholders; no image assets
are included. Audio is created by the existing TTS flow after content approval
and publication, not by the seed. The existing self-review restriction is
unchanged: an author cannot approve their own narration, including the
sole admin account. Permission changes made later through the UI are
preserved on re-seeding because initial grants occur only when creating
the role.

Re-running seed inserts missing baseline records but does **not** remove
obsolete demo rows from a pre-existing database. To get the exact 99-record
baseline, start with a new/empty disposable database.

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

Each domain keeps its HTTP router under `routers/<domain>.py`; services may be
split by cohesive use case under `services/`. Identity uses separate modules for
authentication/session, manager users, and roles. Its `models/`, `schemas/`, and
`repositories/` packages contain one module per database table. A domain may use
`utils/<domain>.py` for small domain-specific helpers that do not belong to the
HTTP, persistence, or security layers; repository modules without an implemented
use case remain placeholders. The Identity layout and dependency rules are
documented in [app/domains/identity/README.md](app/domains/identity/README.md).
Identity additionally keeps password hashing, JWT signing and Refresh Token
generation in its `security/` package; services receive these components through
constructor injection.

Implemented HTTP endpoints:

- `GET /health`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh` using the HttpOnly Refresh Token cookie
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me` with a Bearer Access Token
- `GET|POST /api/v1/manager-users`; GET hỗ trợ `search`,
  `user_status=ACTIVE|INACTIVE`, `offset` và `limit`, đồng thời trả
  `{items, total, offset, limit}`
- `GET|PATCH /api/v1/manager-users/{user_id}`; PATCH có thể đổi mật
  khẩu, khi đó backend băm Argon2id và thu hồi toàn bộ session của tài khoản
- `GET|POST /api/v1/identity/roles`
- `GET|PATCH /api/v1/identity/roles/{role_id}`
- `GET|PUT /api/v1/identity/roles/{role_id}/permissions`
- `GET /api/v1/identity/permissions`
- `GET /api/v1/catalog/regions` returns all regions ordered by ID
- `GET /api/v1/catalog/categories` returns all POI categories ordered by ID
- `GET /api/v1/catalog/languages` returns supported languages ordered by ID
- `/api/v1/admin/catalog/languages` provides permission-protected language
  list/create/update operations. Languages are retired with `UNSUPPORTED` rather
  than hard-deleted.

Language codes retain a database format check for two or three lowercase letters.
The backend additionally validates that submitted codes really belong to ISO
639-1 or ISO 639-2 (including bibliographic and terminology variants).
- `GET /api/v1/pois?offset=0&limit=20` trả
  `{items, total, offset, limit}`
- `GET /api/v1/pois/{poi_id}` where `poi_id` is a string such as
  `poi-010926-951c03a1`

POI management endpoints are available under `/api/v1/admin/pois` with
`POI Management` permissions. They support list/detail, create/update/status,
vô hiệu hóa bằng trạng thái, và region/category form options. Apply migration
`0005_poi_management` before administrative writes. Contracts, architecture,
GROUP 2 compatibility decisions and integration limits are documented in
[the POI domain guide](app/domains/poi/README.md). Narration version/workflow APIs
are available under `/api/v1/admin/poi-contents`, audio metadata under
`/api/v1/admin/audios`, and online narration selection with English fallback at
`GET /api/v1/pois/{poi_id}/narration`. Apply `0006_poi_content_audio` for narration
and audio constraints. Publish tự sinh MP3 bằng gTTS khi chưa có audio, lưu trên
persistent local volume và phục vụ qua `/api/v1/assets/audio`; production object
storage, offline rebuild và audit integration vẫn còn chờ. Frontend callers phải
đọc danh sách phân trang từ trường `items` và dùng
`total` để tính tổng số trang.

POI reads return only records with `poi_status = 'active'`. Identity models,
repositories and management services exist. Passwords are hashed and verified
with Argon2id in the Identity security layer, and RS256 Access Tokens can be signed
and verified with keys injected from configuration. Login, refresh, logout and
current-user endpoints are available. Login persists a session, stores only the
SHA-256 Refresh Token hash, returns the opaque token in a secure HttpOnly cookie,
and binds the Access Token to the session through its `sid` claim. Refresh rotates that cookie;
logout revokes the session so its Access Tokens stop working immediately.
Manager-user and role routes require the matching `User Management` permission
(`read`, `create`, or `update`). Accounts are deactivated through `user_status`
instead of hard-deleted. Nearby search, QR activation, and offline package
generation remain future use cases.

QR-triggered listening ingestion is available at
`POST /api/v1/listening/qr-scans`. The anonymous endpoint resolves an active POI
from `qr_code`, forces `trigger_type=QR_CODE`, and inserts an idempotent
`listening_history` row. Dashboard QR totals should count rows whose trigger is
`QR_CODE`; retry the same request with the same event `id` to avoid double-counting.
Managers with `Listening Analytics/read` can retrieve the all-time listening count
from `GET /api/v1/listening/dashboard`.

## Group 3 — first-build offline package staging

The new `feature/group3-offline-package-manifest-20261106` branch introduces
`OfflinePackageRepository` and `OfflinePackageItemRepository`, plus
`OfflinePackageService.prepare_initial_package()`. It selects active POIs in
the requested region and optional category, with exactly the requested
SUPPORTED language, PUBLISHED narration and valid audio **metadata**.
It inserts a new logical `offline_package` and its `offline_package_item`
membership in **one service-owned transaction**. It returns deterministic
UTF-8 manifest JSON bytes with POI/narration/audio/image metadata.

This is an internal staging service, **not an HTTP API or a live download**.
It intentionally leaves the package `BUILDING` with no manifest URL/checksum
and no `published_at`. Before a package can be marked `PUBLISHED`, a later
release workflow must validate actual asset bytes/URLs, write manifest bytes
to immutable accessible storage, verify their SHA-256, and atomically
commit URL/checksum/version/membership. Currently the schema does not store
image sizes, so `total_size` stays NULL rather than claiming an incorrect
byte count. Rebuilds must stage separately and keep previously published
packages intact. The seed's `cdn.example.local` URLs are placeholders.

The mobile flow after release will be:
fetch published package metadata → GET immutable manifest URL → verify
manifest checksum → compare each asset checksum to the device cache →
download missing audio/images and validate SHA-256 → activate the new
local snapshot. No English fallback is applied inside an offline package.

```powershell
python -m pytest tests/test_offline_repository.py -q -p no:cacheprovider
```

### Comparing a published manifest to current POI data

`OfflinePackageService.plan_rebuild(package_id=..., published_manifest=...)`
reads and validates the **immutable published manifest bytes** against
`offline_package.package_checksum_sha256`, then queries the current
POI/content/audio data for the same filters. It compares canonical item
contents, excluding only `generated_at` and `package_version`, and
returns POI IDs added/removed/updated plus asset URLs whose checksums are
not present in the previous manifest. Changing coordinates, title, script,
audio URL/checksum, or POI eligibility is detected even when item IDs are
unchanged. An unchanged snapshot produces no manifest and no version bump.
No extra SHA columns or database tables are needed.

The rebuild workflow is split into two explicit phases:

1. `plan_rebuild(...)` compares current database rows to previously published,
   SHA-verified manifest bytes without changing the database. If unchanged,
   it returns `manifest=None`, no version increment, and no downloads.
2. Upload the new manifest to an immutable URL and verify actual audio/image
   bytes in external storage. After successful checks,
   `publish_verified_rebuild(plan=..., published_manifest=...,
   manifest_url=..., verify_manifest=..., verify_asset=...)` validates all
   asset checksums, reloads/locks the package, checks its expected version,
   reconstructs the snapshot from current rows, rejects stale plans, and
   synchronizes membership while updating URL/checksum/version in **one DB
   transaction**. Unchanged item IDs/timestamps are preserved.

**Storage verification and automatic scheduling are not implemented**.
Trusted server-side verifier callbacks must be supplied by a later storage
integration; neither user input nor a successful upload alone proves
manifest/resource integrity. PostgreSQL/source changes occurring during
publication still require transaction/concurrency integration tests and
possibly stronger source locking. Keep old immutable manifest URLs and assets
accessible to clients already on the previous version. This design needs
no additional fingerprint columns or tables.

### Persistent local manifest staging storage

Calling `POST /api/v1/admin/offline/packages/prepare` now **also writes**
the generated UTF-8 manifest to immutable local storage. The returned JSON
preview is unchanged, and the package deliberately stays `BUILDING` with
`package_url = NULL` and `package_checksum_sha256 = NULL` until actual assets
and the uploaded manifest have been verified in the future publish workflow.

Directory layout:

```text
offline-manifests/
  staging/
    pack-071126-1234abcd/
      v1/
        manifest.json
```

For Docker Compose the API service mounts a persistent named volume
`offline-manifests` at `/var/lib/mnr/offline-manifests`. The Docker image
creates that directory owned by the unprivileged `app` user. This storage is
**not** PostgreSQL's `postgres-data` volume. To inspect after preparing a
package:

```powershell
docker compose exec api ls -R /var/lib/mnr/offline-manifests/staging
```

For local Uvicorn, set `OFFLINE_MANIFEST_DIR` in `.env` (the example points
to `var/offline/manifests` under the backend working directory). Generated
local files are Git-ignored.

The `FileSystemManifestStorage` adapter in
`app/domains/offline/storage/manifest.py` validates manifest JSON/version,
calculates SHA-256, writes through a temporary file and atomic no-overwrite
link, supports idempotent retries of identical bytes, and provides an internal
checksum-validating reader. Different bytes at the same package/version path
are rejected. No staging directory is mounted publicly: these files are
**not downloadable by mobile yet**. A future publish workflow will verify
the real referenced audio/image URLs and expose only published snapshots,
preserving older published versions. A DB failure after staging may leave
an inaccessible/orphan staged file; never delete the volume to recover it.
No migration or extra SHA column is required.

```powershell
python -m pytest tests/test_offline_manifest_storage.py -q -p no:cacheprovider
```

## Group 3 HTTP endpoints (visible in Swagger)

The Offline routers are registered under `/api/v1`. After pulling this branch
and rebuilding the API image, open `http://localhost:8000/docs` and expand
**Offline Packages** or **Offline Package Management**.

| Method | Path | Access | Contract |
| --- | --- | --- | --- |
| GET | `/api/v1/offline/packages` | Public | Published package page with `items`, `total`, `offset`, `limit` (filter by region/language/category IDs) |
| GET | `/api/v1/offline/packages/{package_id}` | Public | Published package metadata including manifest URL/checksum |
| GET | `/api/v1/admin/offline/packages` | Offline Package Management: read | All-status page with `items`, `total`, `offset`, `limit` |
| GET | `/api/v1/admin/offline/packages/{package_id}` | Offline Package Management: read | Package detail |
| GET | `/api/v1/admin/offline/packages/{package_id}/items` | Offline Package Management: read | Stored package memberships |
| POST | `/api/v1/admin/offline/packages/prepare` | Offline Package Management: create | Create BUILDING package and return a **nonpublished** manifest preview |
| POST | `/api/v1/admin/offline/packages/{package_id}/rebuild/preview` | Offline Package Management: update | Compare against exact UTF-8 published manifest text, checksum-validated against the DB; read-only |

All administrative endpoints require a valid Bearer JWT and matching RBAC
permission, seeded under `Offline Package Management`. The public endpoints
never expose BUILDING or FAILED packages. No `publish` API is exposed yet:
real asset/manifest storage and integrity-verification adapters must be added
first; client-provided flags must not bypass publication checks. Current
`cdn.example.local` seed URLs are placeholders and not real downloadable
assets. The preview endpoint receives exact JSON text rather than a parsed
object so its published SHA-256 can be validated against stored bytes.

Run the route tests without touching PostgreSQL:

```powershell
python -m pytest tests/test_offline_api.py -q -p no:cacheprovider
```

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
