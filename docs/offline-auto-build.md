# Offline package auto-build (event-driven)

## Behavior

Admin never creates or publishes a package. Mobile never triggers a build.
When an ACTIVE POI changes, its region before/after the update is queued.
When narration is PUBLISHED (or published audio is updated), the affected
region/language is queued. The queue entry is committed together with the
source change; rolled-back edits do not create jobs.

The worker rebuilds existing packages and creates the **base Region+Language**
package as soon as eligible POI/content/audio exists. Existing category-filtered
packages are kept current, but creation of every category combination is deferred
until product requirements are finalized.

Eligibility: ACTIVE POI, exact-language PUBLISHED narration and verified audio;
no English fallback for an offline package. Manifest references shared assets;
there is no per-package ZIP. Worker verifies bytes and SHA-256 before publication.

First build: BUILDING -> PUBLISHED (or FAILED on an error, with retry).
Rebuild: previously PUBLISHED release remains available until the new version
passes verification and the database transaction commits. No content diff means
no version bump. Unused/orphan manifest files from unsuccessful publications
are not accessible through the public endpoint.

## Operation

Run migration \`alembic upgrade head\`, then start API and worker:

\`\`\`bash
docker compose --profile api up --build -d
\`\`\`

For a locally run API, separately run \`python -m scripts.offline_worker\` with
the same DATABASE_URL and shared manifest/audio/image directories. The worker
polls the durable queue every 5 seconds, retries with bounded exponential
backoff, and reclaims abandoned jobs after 15 minutes.

Set **OFFLINE_MANIFEST_PUBLIC_BASE_URL** to the externally reachable API prefix
\`https://YOUR_HOST/api/v1/offline/manifests\`. Likewise configure
TTS_AUDIO_PUBLIC_BASE_URL and POI_IMAGE_PUBLIC_BASE_URL so real mobile devices
can download assets; localhost only works for same-device development.

Mobile discovery: \`GET /api/v1/offline/packages\`, details:
\`GET /api/v1/offline/packages/{id}\`.
The package URL points to
\`GET /api/v1/offline/manifests/{id}/v{version}/{sha256}.json\`.
Only releases committed in \`offline_package_release\` are served; previous
verified versions remain addressable after rebuild.

There is no Admin POST /prepare or POST /publish: package creation is internal.
Admin read-only lists and optional rebuild preview remain.

## Known deployment considerations

Remote asset URLs must stay reachable; byte-level checks can require network
traffic. Configure public HTTPS URLs and shared persistent storage for the API
and worker. If source data changes during a build, the service refuses to
publish a stale snapshot and the queued follow-up request can retry. Existing
catalog data created before this feature needs a one-time event/backfill or a
POI update before a package is built. Database migrations and runtime tests
must be exercised against PostgreSQL and real storage before production use.
