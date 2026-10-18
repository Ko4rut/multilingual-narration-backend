---
name: mnr-backend
description: Implement or review APIs, domain services, SQLAlchemy models, Alembic migrations and tests in the Multilingual Narration backend using its existing FastAPI domain architecture. Use for this repository's backend work, not unrelated frontend or mobile changes.
---

# MNR backend implementation

Use this skill with the repository's [AGENTS.md](../../AGENTS.md), which owns the
shared architecture rules. Paths below are relative to the backend root. Explicit
user instructions override skill conventions. Complete the requested feature;
do not treat this workflow as permission to implement adjacent use cases.

## Locate the use case

Read the relevant domain, its tests and the router composition. Inspect the current
working-tree diff to distinguish existing edits. Consult README for runtime setup.

| Domain | Ownership |
| --- | --- |
| `poi` | PointOfInterest, PoiCategory, PoiCategoryMapping; map/QR/POI management |
| `narration` | PoiContent, ContentAudio; language selection, publishing, TTS |
| `catalog` | Region, Language |
| `identity` | ManagementUser, Role, RolePermission, Permission, Action, ManagementFunction |
| `listening` | ListeningHistory; playback events and analytics |
| `offline` | OfflinePackage; optional package use case |
| `audit` | AuditLog; administrative change history |

At skeleton creation, only health and POI list/detail endpoints were implemented.
Check current source before assuming that remains true. A model or empty file is
not evidence of an implemented use case. The use-case document does not specify
every detail of auth, language fallback, geofence priority, TTS providers or offline
packaging. Resolve decisions affecting the requested behavior from existing code
or user requirements; ask only if a material decision remains missing.

## Implement a vertical slice

1. Define the HTTP contract: path/method, request/response schema, visibility or
   permission requirements, validation and expected errors. Preserve existing
   contracts unless the requested change requires otherwise.
2. Add/change domain schemas and only the model fields needed. For persistence
   changes, follow the migration procedure below.
3. Implement explicit repository methods with the injected Session. Keep query
   ordering stable for pagination. Let the database enforce unique/FK constraints;
   a pre-check alone does not prevent conflicting concurrent writes.
4. Implement the service use case. Coordinate related writes in a single
   transaction, starting before queries. A repository may `flush()` when IDs are
   needed, but the service owns commit/rollback. Translate known constraint errors
   after rollback into an appropriate domain error without hiding unrelated errors.
5. Wire service dependencies in the domain router and add it to `app/route/api.py`
   if new. Declare `response_model`; do not serialize arbitrary ORM dictionaries.
   Add HTTP mappings for new domain errors in the application boundary.
6. Verify the observable behavior and update documentation affected by the change.

Working examples to inspect rather than copy blindly:
`app/domains/poi/{router,schemas,service,repository,models}.py`,
`app/route/dependencies.py`, and `tests/test_api.py`.
The POI example is read-only; do not infer write transaction handling from it.

Avoid creating generic CRUD base classes, provider integrations or extra layers
unless the requested use case demonstrates a need. Cross-domain orchestration
should use explicit service/repository collaborators, not HTTP calls to this app.

## Model and migration changes

- Inspect the existing migration and database model before generating a revision.
  Add new model exports to `app/models.py`. Maintain a single metadata registry.
- Generate a revision against a known development/test schema, inspect the diff,
  and keep only intended operations. Autogenerate is a draft, especially for renames
  and data transformations. Do not rewrite the initial revision to alter an already
  initialized database.
- Validate upgrade and relevant constraints on an isolated PostgreSQL database.
  Validate downgrade there when a reversible downgrade is part of the change.
  Never downgrade or reset the user's populated database as a routine test.
- Run `alembic check` against the upgraded test schema. For a model-only refactor,
  no new operations should be detected. Unexpected drift requires investigation,
  not an unrelated schema reset.
- Preserve existing seed natural keys and update schema tests if the intended
  table set changes. SQLite is not a substitute for PostgreSQL JSONB/constraint
  integration checks in this project.

## Validation and completion

Use the existing interpreter. From this checkout in PowerShell:

```powershell
.\venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
.\venv\Scripts\python.exe -m alembic check
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

These are task-specific options, not a requirement to start servers or contact the
database for every edit. Tests disable the cache to avoid this workspace's cache
permission issue. `alembic check` uses configured database credentials; verify
the target first and do not print them. Use an explicitly isolated `DATABASE_URL`
for integration tests that write data. `/health` is liveness only, not database
readiness. Docker Compose currently supplies PostgreSQL and a migration/seed job;
inspect it before claiming it launches the API.

For changed API behavior, cover success, invalid input, missing/hidden resources
and applicable access checks. Dependency overrides and repository fakes are useful
for HTTP/service tests, but cannot prove SQL filters or transaction rollback;
test those against isolated PostgreSQL when changed. No need to add tests that
merely assert file layout or repeat implementation wording.

Before finishing, inspect the diff for layer violations and unrelated changes.
Report what works, exact relevant validation results, migration implications and
any part not tested. Never describe an unimplemented provider or placeholder as
complete.
