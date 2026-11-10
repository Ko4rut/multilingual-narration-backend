from contextlib import nullcontext
from datetime import datetime, timezone

import pytest

from app.domains.poi.exceptions import PoiPermissionDenied
from app.domains.poi.models.poi_content import PoiContent
from app.domains.poi.schemas.poi_content import PoiContentReview
from app.domains.poi.services.poi_content import PoiContentService


class SessionStub:
    def begin(self):
        return nullcontext()

    def flush(self) -> None:
        pass


class PoiRepositoryStub:
    def get_by_id(self, poi_id: str, *, for_update: bool = False):
        return object()


class ContentRepositoryStub:
    def __init__(self, content: PoiContent):
        self.content = content

    def get_by_id(self, content_id: str, *, for_update: bool = False):
        return self.content


class AudioRepositoryStub:
    def get_for_contents(self, content_ids: list[str]):
        return {}


def make_content() -> PoiContent:
    return PoiContent(
        id="cont-010126-12345678",
        poi_id="poi-010126-12345678",
        language_id="lang-12345678",
        narration_title="Title",
        narration_script="Script",
        content_version=1,
        content_status="WAITING_APPROVAL",
        created_by="user-author",
        approved_by=None,
        published_by=None,
        created_at=datetime.now(timezone.utc),
        approved_at=None,
        published_at=None,
    )


def build_service(content: PoiContent) -> PoiContentService:
    return PoiContentService(
        SessionStub(), PoiRepositoryStub(),
        ContentRepositoryStub(content), AudioRepositoryStub(),
    )


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [("APPROVE", "APPROVED"), ("REJECT", "REJECTED")],
)
def test_review_applies_decision(decision: str, expected_status: str) -> None:
    content = make_content()

    result = build_service(content).review_content(
        content.id, PoiContentReview(decision=decision), actor_id="user-reviewer",
    )

    assert result.content_status == expected_status
    assert content.content_status == expected_status
    if decision == "APPROVE":
        assert content.approved_by == "user-reviewer"
        assert content.approved_at is not None
    else:
        assert content.approved_by is None
        assert content.approved_at is None


def test_author_cannot_review_own_content() -> None:
    content = make_content()

    with pytest.raises(PoiPermissionDenied):
        build_service(content).review_content(
            content.id,
            PoiContentReview(decision="APPROVE"),
            actor_id=content.created_by,
        )
