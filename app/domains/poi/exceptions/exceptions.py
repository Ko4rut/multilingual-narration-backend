from app.core.exceptions import ResourceNotFound


class PoiNotFound(ResourceNotFound):
    pass


class PoiReferenceNotFound(ResourceNotFound):
    pass


class PoiConflict(Exception):
    """A POI change conflicts with data or publication rules."""


class InvalidPoiFilter(Exception):
    pass


class InvalidPoiImage(Exception):
    """Ảnh POI không thể tải hoặc không đáp ứng yêu cầu an toàn."""


class InvalidAudioAsset(Exception):
    """Audio không thể tải hoặc metadata thực tế không hợp lệ."""


class InvalidPoiQrCode(Exception):
    """Payload QR không thuộc định dạng POI do hệ thống phát hành."""


class NarrationNotFound(ResourceNotFound):
    pass


class TtsGenerationFailed(Exception):
    """Không thể tạo hoặc lưu audio TTS để hoàn tất publish."""
