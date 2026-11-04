"""Helpers shared by the offline package seed and future build service."""


def make_package_key(
    *,
    region_code: str,
    language_code: str,
    category_code: str | None = None,
) -> str:
    """Return the canonical Group 3 filter key using stored catalog codes."""
    if not region_code or not language_code:
        raise ValueError("region_code and language_code are required")
    components = []
    if category_code is not None:
        if not category_code:
            raise ValueError("category_code must not be blank")
        components.append(f"cat:{category_code}")
    components.extend((f"region:{region_code}", f"lang:{language_code}"))
    return "|".join(components)
