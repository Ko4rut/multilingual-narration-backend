from collections.abc import Callable
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domains.identity.exceptions import (
    PermissionNotFound,
    RoleNameAlreadyExists,
    RoleNotFound,
)
from app.domains.identity.models.permission import PermissionModel
from app.domains.identity.models.role import RoleModel
from app.domains.identity.models.role_permission import RolePermissionModel
from app.domains.identity.repositories.permission import PermissionRepository
from app.domains.identity.repositories.role import RoleRepository
from app.domains.identity.repositories.role_permission import RolePermissionRepository
from app.domains.identity.utils.identity import (
    generate_dated_identifier,
    required_text,
    utc_now,
)


class RoleService:
    """Các ca sử dụng quản lý vai trò và tập quyền của vai trò."""

    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        session: Session | None = None,
        role_permission_repository: RolePermissionRepository | None = None,
        *,
        clock: Callable[[], datetime] = utc_now,
        id_factory: Callable[[str, datetime], str] = generate_dated_identifier,
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.session = session
        self.role_permission_repository = role_permission_repository
        self.clock = clock
        self.id_factory = id_factory

    def get_role(self, role_id: str) -> RoleModel:
        """Lấy vai trò theo mã hoặc báo lỗi nếu không tồn tại."""

        role = self.role_repository.get_by_id(role_id)
        if role is None:
            raise RoleNotFound("Role not found")
        return role

    def list_roles(self) -> list[RoleModel]:
        """Liệt kê toàn bộ vai trò."""

        return self.role_repository.get_all()

    def list_role_permissions(self, role_id: str) -> list[PermissionModel]:
        """Liệt kê quyền của một vai trò đã tồn tại."""

        self.get_role(role_id)
        return self.permission_repository.get_all_by_role_id(role_id)

    def list_permissions(self) -> list[PermissionModel]:
        """Liệt kê permission catalog để giao diện cấu hình role sử dụng."""

        return self.permission_repository.get_all()

    def create_role(
        self,
        *,
        name: str,
        description: str | None,
        permission_ids: list[str],
        actor_user_id: str,
    ) -> RoleModel:
        """Tạo role và gán tập permission ban đầu trong cùng transaction."""

        session, role_permissions = self._write_collaborators()
        normalized_name = required_text(name, "name")
        normalized_description = self._optional_text(description)
        unique_permission_ids = list(dict.fromkeys(permission_ids))
        now = self.clock()
        try:
            with session.begin():
                if self.role_repository.get_by_name(normalized_name) is not None:
                    raise RoleNameAlreadyExists("Role name already exists")
                self._require_permissions(unique_permission_ids)
                role = RoleModel(
                    id=self.id_factory("role", now),
                    name=normalized_name,
                    description=normalized_description,
                    created_by=actor_user_id,
                    last_updated_by=actor_user_id,
                    created_at=now,
                    last_updated_at=now,
                )
                self.role_repository.add(role)
                for permission_id in unique_permission_ids:
                    role_permissions.add(
                        RolePermissionModel(
                            role_id=role.id,
                            permission_id=permission_id,
                        )
                    )
                session.flush()
        except IntegrityError as exc:
            self._translate_role_integrity_error(exc)
        return role

    def update_role(
        self,
        role_id: str,
        *,
        actor_user_id: str,
        name: str | None = None,
        description: str | None = None,
        update_description: bool = False,
    ) -> RoleModel:
        """Cập nhật metadata role và người thực hiện thay đổi."""

        session, _role_permissions = self._write_collaborators()
        now = self.clock()
        try:
            with session.begin():
                role = self.get_role(role_id)
                changed = False
                if name is not None:
                    normalized_name = required_text(name, "name")
                    if normalized_name != role.name:
                        duplicate = self.role_repository.get_by_name(normalized_name)
                        if duplicate is not None:
                            raise RoleNameAlreadyExists("Role name already exists")
                        role.name = normalized_name
                        changed = True
                if update_description:
                    normalized_description = self._optional_text(description)
                    if normalized_description != role.description:
                        role.description = normalized_description
                        changed = True
                if changed:
                    role.last_updated_by = actor_user_id
                    role.last_updated_at = now
                    session.flush()
        except IntegrityError as exc:
            self._translate_role_integrity_error(exc)
        return role

    def replace_role_permissions(
        self,
        role_id: str,
        *,
        permission_ids: list[str],
        actor_user_id: str,
    ) -> list[PermissionModel]:
        """Thay toàn bộ tập quyền của role theo cách nguyên tử."""

        session, role_permissions = self._write_collaborators()
        now = self.clock()
        unique_permission_ids = list(dict.fromkeys(permission_ids))
        with session.begin():
            role = self.get_role(role_id)
            self._require_permissions(unique_permission_ids)
            existing = {
                item.permission_id
                for item in role_permissions.get_all_by_role_id(role_id)
            }
            requested = set(unique_permission_ids)
            for permission_id in existing - requested:
                role_permissions.remove(role_id, permission_id)
            for permission_id in requested - existing:
                role_permissions.add(
                    RolePermissionModel(
                        role_id=role_id,
                        permission_id=permission_id,
                    )
                )
            role.last_updated_by = actor_user_id
            role.last_updated_at = now
            session.flush()
            permissions = self.permission_repository.get_all_by_role_id(role_id)
        return permissions

    def _require_permissions(self, permission_ids: list[str]) -> None:
        for permission_id in permission_ids:
            if self.permission_repository.get_by_id(permission_id) is None:
                raise PermissionNotFound("Permission not found")

    def _write_collaborators(
        self,
    ) -> tuple[Session, RolePermissionRepository]:
        if self.session is None or self.role_permission_repository is None:
            raise RuntimeError("RoleService write collaborators are not configured")
        return self.session, self.role_permission_repository

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _translate_role_integrity_error(exc: IntegrityError) -> None:
        diagnostic = getattr(exc.orig, "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None)
        if constraint_name == "role_name_key":
            raise RoleNameAlreadyExists("Role name already exists") from exc
        if constraint_name == "role_permission_permission_id_fkey":
            raise PermissionNotFound("Permission not found") from exc
        raise exc
