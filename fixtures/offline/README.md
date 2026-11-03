# Hanoi offline manifest seed (Group 3)

This fixture describes 2 logical packages / 4 MP3s using the existing Hanoi POIs
and published Vietnamese/English narration rows in scripts/seed.py.

## Add these files

Place four real playable MP3 files under fixtures/offline/audio/:

    han-van-mieu-vi.mp3
    han-van-mieu-en.mp3
    han-ho-guom-vi.mp3
    han-ho-guom-en.mp3

## Generate manifests after adding the MP3s

Start PostgreSQL, apply existing migrations and run the existing seed using a
development/test database. Then run:

    python -m alembic upgrade head
    python -m scripts.seed
    python -m scripts.build_demo_offline_manifests --media-base-url https://your-media-host.example/media

The base URL must be the REAL address serving /audio/<filename>.mp3.
This backend currently has no static media route and this script uploads nothing.

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
