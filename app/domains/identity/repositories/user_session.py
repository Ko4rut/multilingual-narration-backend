from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.identity.models.user_session import UserSessionModel


class UserSessionRepository:

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, session_id: str) -> UserSessionModel | None:
        # Lấy phiên đăng nhập theo ID.
        return self.session.get(UserSessionModel, session_id)

    def get_by_refresh_token_hash_for_update(self, refresh_token_hash: str) -> UserSessionModel | None:
        # Lấy và khóa phiên để hai request không thể xoay cùng token.
        statement = (
            select(UserSessionModel)
            .where(UserSessionModel.refresh_token_hash == refresh_token_hash)
            .with_for_update()
        )
        return self.session.scalar(statement)

    def get_all_by_user_id(self, user_id: str) -> list[UserSessionModel]:
        # Lấy các phiên của user, ưu tiên phiên được tạo gần nhất.
        statement = (
            select(UserSessionModel)
            .where(UserSessionModel.user_id == user_id)
            .order_by(UserSessionModel.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def add(self, user_session: UserSessionModel) -> None:
        # Đưa phiên mới vào Session; service chịu trách nhiệm commit.
        self.session.add(user_session)

    def revoke_all_active_for_user(self, user_id: str, revoked_at: datetime,) -> None:
        # Đánh dấu thu hồi cho mọi phiên chưa bị thu hồi của user.
        statement = select(UserSessionModel).where(
            UserSessionModel.user_id == user_id,
            UserSessionModel.revoked_at.is_(None),
        )
        for user_session in self.session.scalars(statement):
            user_session.revoked_at = revoked_at
