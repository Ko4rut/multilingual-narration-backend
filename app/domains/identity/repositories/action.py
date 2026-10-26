from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.identity.models.action import ActionModel


class ActionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, action_id: str) -> ActionModel | None:
        return self.session.get(ActionModel, action_id)

    def get_by_name(self, name: str) -> ActionModel | None:
        return self.session.scalar(select(ActionModel).where(ActionModel.name == name))

    def list_all(self) -> list[ActionModel]:
        return list(
            self.session.scalars(select(ActionModel).order_by(ActionModel.name))
        )
