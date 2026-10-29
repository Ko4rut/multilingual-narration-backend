from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.identity.models.action import ActionModel


class ActionRepository:
    
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, action_id: str) -> ActionModel | None:
        # Lấy một hành động theo ID
        return self.session.get(ActionModel, action_id)

    def get_by_name(self, name: str) -> ActionModel | None:
        # Lấy một hành động theo tên duy nhất.
        return self.session.scalar(select(ActionModel).where(ActionModel.name == name))

    def get_all(self) -> list[ActionModel]:
        # Lấy toàn bộ hành động hiện có.
        return list(self.session.scalars(select(ActionModel)))
