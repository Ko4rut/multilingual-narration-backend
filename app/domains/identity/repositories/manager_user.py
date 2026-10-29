from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.identity.models.manager_user import ManagerUserModel


class ManagerUserRepository:
    
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: str) -> ManagerUserModel | None:
        # Lấy tài khoản quản trị theo ID.
        return self.session.get(ManagerUserModel, user_id)

    def get_by_email(self, email: str) -> ManagerUserModel | None:
        # Lấy tài khoản theo email đã được service chuẩn hóa.
        return self.session.scalar(select(ManagerUserModel).where(ManagerUserModel.email == email))

    def get_all(self, *, offset: int, limit: int) -> list[ManagerUserModel]:
        # Lấy danh sách tài k`hoản theo phân trang ``offset``/``limit``.
        return list(self.session.scalars(
            select(ManagerUserModel)
            .order_by(ManagerUserModel.created_at)
            .offset(offset)
            .limit(limit)
        ))
    
    def add(self, manager_user: ManagerUserModel) -> None:
        # Đưa tài khoản mới vào Session; service chịu trách nhiệm commit.
        self.session.add(manager_user)
