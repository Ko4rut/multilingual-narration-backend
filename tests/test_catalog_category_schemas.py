import pytest
from pydantic import ValidationError

from app.domains.catalog.schemas import PoiCategoryCreate, PoiCategoryUpdate


def test_create_category_validates_and_normalizes_name():
    category = PoiCategoryCreate(
        category_name="  Museum of Art  ", category_code="art-museum",
    )
    assert category.model_dump() == {
        "category_name": "Museum of Art",
        "category_code": "art-museum",
    }


@pytest.mark.parametrize("code", [
    "", "MUSEUM", "my_space", "has space", "-start", "end-", "two--hyphens",
    "x" * 31, "đền",
])
def test_create_category_rejects_invalid_code(code):
    with pytest.raises(ValidationError):
        PoiCategoryCreate(category_name="Museum", category_code=code)


@pytest.mark.parametrize("name", ["", "  ", "n" * 121])
def test_category_rejects_invalid_names(name):
    with pytest.raises(ValidationError):
        PoiCategoryCreate(category_name=name, category_code="museum")
    with pytest.raises(ValidationError):
        PoiCategoryUpdate(category_name=name)


def test_update_only_accepts_name_and_requires_one():
    assert PoiCategoryUpdate(category_name=" New name ").category_name == "New name"
    with pytest.raises(ValidationError):
        PoiCategoryUpdate.model_validate({})
    with pytest.raises(ValidationError):
        PoiCategoryUpdate.model_validate({"category_code": "new-code", "category_name": "New"})
    with pytest.raises(ValidationError):
        PoiCategoryCreate.model_validate({
            "category_name": "Museum", "category_code": "museum",
            "id": "cat-forged",
        })
