from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domains.identity.models.manager_user import (
    ManagerUserModel,
    ManagerUserStatus,
)


class ManagerUserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: str) -> ManagerUserModel | None:
        # Lấy tài khoản quản trị theo ID.
        return self.session.get(ManagerUserModel, user_id)

    def get_by_email(self, email: str) -> ManagerUserModel | None:
        # Lấy tài khoản theo email đã được service chuẩn hóa.
        return self.session.scalar(
            select(ManagerUserModel).where(ManagerUserModel.email == email)
        )

    def get_all(
        self,
        *,
        offset: int,
        limit: int,
        search: str | None = None,
        user_status: ManagerUserStatus | None = None,
    ) -> list[ManagerUserModel]:
        """Lấy danh sách tài khoản theo tìm kiếm, trạng thái và phân trang."""

        statement = select(ManagerUserModel)
        if search is not None:
            # Escape wildcard để '%' và '_' trong từ khóa được tìm như ký tự
            # thông thường thay vì làm thay đổi phạm vi câu truy vấn LIKE.
            escaped_search = (
                search.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped_search}%"
            statement = statement.where(
                or_(
                    ManagerUserModel.id.ilike(pattern, escape="\\"),
                    ManagerUserModel.email.ilike(pattern, escape="\\"),
                    ManagerUserModel.full_name.ilike(pattern, escape="\\"),
                )
            )
        if user_status is not None:
            statement = statement.where(
                ManagerUserModel.user_status == user_status
            )

        statement = (
            statement.order_by(
                ManagerUserModel.created_at,
                ManagerUserModel.id,
            )
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def add(self, manager_user: ManagerUserModel) -> None:
        # Đưa tài khoản mới vào Session; service chịu trách nhiệm commit.
        self.session.add(manager_user)
