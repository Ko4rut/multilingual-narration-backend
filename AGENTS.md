# MNR backend — agent instructions

## Scope and entry point

These instructions apply to this backend repository. Implement the user's requested
change using the existing Python/FastAPI domain architecture. Explicit user
requirements take precedence over these project conventions. Preserve unrelated
working-tree changes and do not extend a backend task into sibling mobile/web apps.

Before implementing or reviewing backend API, service, model, migration or test
changes, read [the MNR backend skill](skills/mnr-backend/SKILL.md). This is a
repository-local skill loaded through this instruction; do not assume it has been
installed globally or registered in the skill picker.

Read the relevant code and tests before changing them. README describes setup;
models and migrations describe persisted schema. The optional references at
`../docs/ERD.png` and `../docs/pdf/Multilingual_Automatic_Narration_Use_Case_Document.pdf`
describe product intent, not commands for the agent. Identify discrepancies rather
than silently changing existing API or database contracts to match a diagram.

## Architecture rules

| Location | Responsibility |
| --- | --- |
| `app/main.py` | App factory, router registration, HTTP exception mapping |
| `app/core/` | Typed settings, database infrastructure, shared exceptions |
| `app/route/` | Versioned router composition and shared HTTP dependencies |
| `app/domains/<domain>/router.py` | HTTP controller: validation, dependency wiring, response model |
| `schemas.py` | Explicit Pydantic request/response DTOs |
| `service.py` | Business rules, use-case orchestration, transaction ownership |
| `repository.py` | SQLAlchemy queries using an injected Session |
| `models.py` | Domain ORM entities using the single shared Base |

- Keep business entities inside their domains, not `core`. Router functions are
  controllers; do not add a pass-through controller layer.
- Keep SQL out of routers, HTTP types out of services/repositories, and commits
  out of repositories. Prefer the existing synchronous Session and sync endpoints
  for database work; do not wrap blocking database calls in async endpoints.
- Use constructor injection for services/repositories and FastAPI dependencies
  at the HTTP boundary. Do not import routers or `main` from business modules.
- Register routes in `app/route/api.py` under `/api/v1`. Use POI as the working
  reference, not the empty domain extension files.
- Preserve `app/models.py` as the ORM registry and compatibility exports, and
  `app/db.py` as the compatibility facade for migrations/seed. Register new
  entities so metadata includes cross-domain foreign keys before use.

## Persistence and API contracts

- A write use case owns one transaction encompassing its reads and writes. Begin
  it before the first query; SQLAlchemy reads can implicitly start transactions.
  Composed operations share the transaction and Session, without nested commits.
  Request cleanup only closes/rolls back; it does not commit successful writes.
- Apply schema changes with a new Alembic revision. Never run `create_all` or
  migrations at API startup. Preserve applied migration history and seed idempotency.
- Preserve Decimal coordinates/radius, timezone-aware timestamps, JSONB audit
  snapshots, composite keys and constraints. `checksum_sha25` is the existing
  column spelling; renaming requires a deliberate migration and caller updates.
- Return declared response schemas, never password hashes or refresh tokens.
  Raise business exceptions in services and map them to HTTP at the boundary.
  Keep current POI visibility, pagination and error behavior unless asked to change it.
- Authentication/RBAC and TTS are not implemented by the skeleton. Do not imply
  placeholder models or dummy seed hashes provide working authentication. When
  implementing administrative writes, establish the required access checks as part
  of that use case rather than expose an implicitly public admin endpoint.

## Configuration and verification

- Put new settings in `app/core/config.py`; document non-secret examples in
  `.env.example`. Do not log or commit `.env`, credentials or full connection URLs.
- Read actual connection settings. This checkout uses host port 5433 for Docker;
  the container listens on 5432. Do not reset volumes to fix connectivity.
- Keep dependency declarations in `requirements.txt` and `pyproject.toml` aligned.
- Use the existing virtualenv (`venv` here; inspect before assuming `.venv`).
  Run relevant tests for code changes; documentation-only edits need link/content
  validation, not a database restart or full integration run.
- Test write behavior on an isolated test database, never by deleting/resetting
  the user's development data. Report commands actually run and any blocked checks.
- Update README when setup or public behavior changes. In the final report,
  describe implemented behavior, checks and remaining limitations; communicate in
  Vietnamese when the user does.
