"""Tạo payload và ảnh QR ổn định dùng để nhận diện POI."""

from io import BytesIO
import re

import qrcode
from qrcode.constants import ERROR_CORRECT_M


POI_QR_PATTERN = re.compile(r"^mnr://pois/(poi-\d{6}-[a-z0-9]{8})$")


def create_poi_qr_payload(poi_id: str) -> str:
    """Tạo deep-link ổn định để ứng dụng nhận diện POI sau khi quét QR."""
    return f"mnr://pois/{poi_id}"


def parse_poi_qr_payload(payload: str) -> str | None:
    """Trích POI ID khi payload đúng định dạng QR do hệ thống phát hành."""
    match = POI_QR_PATTERN.fullmatch(payload.strip())
    return match.group(1) if match is not None else None


def render_qr_png(payload: str) -> bytes:
    """Render payload thành PNG với mức sửa lỗi trung bình và quiet zone chuẩn."""
    # version=None kết hợp fit=True để thư viện tự chọn kích thước QR nhỏ nhất
    # chứa đủ payload. Border 4 là quiet zone tối thiểu theo chuẩn QR.
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    # Trả bytes thay vì tự ghi file để router quyết định cách trả hoặc lưu ảnh.
    image = qr.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
