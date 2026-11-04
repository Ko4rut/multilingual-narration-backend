from secrets import token_hex


def generate_catalog_identifier(prefix: str) -> str:
    """Generate identifiers in the documented prefix-xxxxxxxx format."""

    return f"{prefix}-{token_hex(4)}"
