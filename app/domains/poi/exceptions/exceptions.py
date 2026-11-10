from app.core.exceptions import ResourceNotFound


class PoiNotFound(ResourceNotFound):
    pass


class PoiReferenceNotFound(ResourceNotFound):
    pass


class PoiConflict(Exception):
    """A POI change conflicts with data or publication rules."""


class InvalidPoiFilter(Exception):
    pass


class NarrationNotFound(ResourceNotFound):
    pass


class PoiPermissionDenied(Exception):
    pass
