from io import BytesIO

from PIL import Image

from app.domains.poi.providers.qr_code import create_poi_qr_payload, render_qr_png


def test_create_poi_qr_payload_uses_stable_deep_link() -> None:
    poi_id = "poi-111126-12345678"

    assert create_poi_qr_payload(poi_id) == "mnr://pois/poi-111126-12345678"


def test_render_qr_png_returns_valid_png() -> None:
    content = render_qr_png("mnr://pois/poi-111126-12345678")

    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(content)) as image:
        assert image.format == "PNG"
        assert image.width == image.height
        assert image.width > 0
