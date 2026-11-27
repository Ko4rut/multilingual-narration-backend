class LanguageNotFound(Exception):
    """Requested language does not exist."""


class LanguageAlreadyExists(Exception):
    """Language code or name conflicts with an existing record."""


class PoiCategoryNotFound(Exception):
    """Requested POI Category does not exist."""


class PoiCategoryAlreadyExists(Exception):
    """Category name or code conflicts with an existing record."""


class PoiCategoryInUse(Exception):
    """Category is still referenced by POIs or offline packages."""
