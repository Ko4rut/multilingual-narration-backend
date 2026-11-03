# Hanoi offline manifest seed (Group 3)

This fixture describes 2 logical packages / 4 MP3s using the existing Hanoi POIs
and published Vietnamese/English narration rows in scripts/seed.py.

## Add these files

Place four real playable MP3 files under fixtures/offline/audio/:

    han-van-mieu-vi.mp3
    han-van-mieu-en.mp3
    han-ho-guom-vi.mp3
    han-ho-guom-en.mp3

## Docker Compose (default services, no profile)

From the repository root, after adding all four MP3s:

    docker compose up --build -d

Compose runs PostgreSQL -> migrate/seed -> offline-manifest-init. The media
Nginx service starts after the manifest generation succeeds. Check the output:

    docker compose logs offline-manifest-init
    docker compose ps

On the host, try:

- http://localhost:9000/audio/han-van-mieu-vi.mp3
- http://localhost:9000/generated/region-HAN-lang-vi/v1/manifest.json
- http://localhost:9000/generated/region-HAN-lang-en/v1/manifest.json

The default media host port is 9000 (override MEDIA_PORT). The URLs embedded
in the manifest default to http://localhost:9000 (override MEDIA_BASE_URL).
When accessing from a physical phone, use a reachable LAN host/IP instead of
localhost. Change both settings together if overriding the media port.

The init job uses HOST_UID/HOST_GID (default 1000:1000) to write generated
files into the host's bind-mounted fixtures directory. On Linux with a
different UID/GID, set those variables before running Compose.

Restarting Compose with the same source MP3s, POI/content rows and base URL
verifies and reuses existing v1 manifests. It refuses to overwrite v1 if the
inputs change; a real rebuild must create and publish v2 at a new immutable URL.

## Optional local generation

With PostgreSQL migrated and seeded, run:

    python -m scripts.build_demo_offline_manifests --media-base-url http://localhost:9000

The media service serves /audio/<filename>.mp3 from the mounted fixture
directory. The generator itself does not upload or publish any file.

The script queries real IDs/metadata from the seeded database, computes SHA-256
and sizes from file bytes, and writes:

    fixtures/offline/generated/region-HAN-lang-vi/v1/manifest.json
    fixtures/offline/generated/region-HAN-lang-en/v1/manifest.json
    fixtures/offline/generated/manifest-index-v1.json

It does not change database rows or mark packages PUBLISHED. The existing
scripts/seed.py has fake audio URL/checksum/size metadata and ZIP package URLs.
The manifest generator deliberately does not treat these as real assets.
Reconcile ContentAudio to the uploaded audio, make the media URLs reachable,
upload and verify the manifests, then implement atomic publish separately.

POI images from the existing seed also use example URLs and fake checksums.
These manifests cover audio only; real image assets are still needed for a
complete offline package. No base64 data is stored in PostgreSQL or JSON.

Do not overwrite a versioned manifest file while a client might use it.
The generator refuses to overwrite v1; a rebuild should publish v2 at a new path.
