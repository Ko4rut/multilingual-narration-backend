class LanguageNotFound(Exception):
    """Requested language does not exist."""


class LanguageAlreadyExists(Exception):
    """Language code or name conflicts with an existing record."""


class LanguageInUse(Exception):
    """Language is referenced by content or an offline package."""
