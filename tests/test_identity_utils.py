import pytest

from app.domains.identity.utils import normalize_email, required_text


def test_normalize_email_trims_and_lowercases_valid_email() -> None:
    assert normalize_email("  Admin@MNR.Local ") == "admin@mnr.local"


@pytest.mark.parametrize("email", ["", "missing-at.example.com", "a@b"])
def test_normalize_email_rejects_invalid_email(email: str) -> None:
    with pytest.raises(ValueError, match="valid email address"):
        normalize_email(email)


def test_required_text_trims_value_and_rejects_blank_text() -> None:
    assert required_text("  User Management  ", "function_name") == (
        "User Management"
    )

    with pytest.raises(ValueError, match="function_name must not be empty"):
        required_text("   ", "function_name")
