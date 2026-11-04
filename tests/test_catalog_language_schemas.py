import pytest
from pydantic import ValidationError

from app.domains.catalog.schemas import LanguageCreate


@pytest.mark.parametrize("code", ["ger", "deu", "fre", "fra", "chi", "zho"])
def test_language_create_accepts_iso_639_2_bibliographic_and_terminology_codes(code):
    payload = LanguageCreate(
        language_code=code,
        language_name="Test language",
        language_status="SUPPORTED",
    )
    assert payload.language_code == code


@pytest.mark.parametrize("code", ["cmn", "yue"])
def test_language_create_rejects_codes_only_in_iso_639_3(code):
    with pytest.raises(ValidationError):
        LanguageCreate(
            language_code=code,
            language_name="Test language",
            language_status="SUPPORTED",
        )
