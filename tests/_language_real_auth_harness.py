"""Full-stack Language admin harness executed in an isolated subprocess."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from secrets import token_hex, token_urlsafe

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session


database_url = os.environ["TEST_DATABASE_URL"]
os.environ["DATABASE_URL"] = database_url

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
os.environ["JWT_PRIVATE_KEY"] = private_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
public_key = private_key.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()
os.environ["JWT_PUBLIC_KEYS"] = json.dumps({"language-test": public_key})
os.environ["JWT_ACTIVE_KEY_ID"] = "language-test"
os.environ["AUTH_COOKIE_SECURE"] = "false"

from fastapi.testclient import TestClient

from app.domains.catalog.models import Language
from app.domains.identity.models.action import ActionModel
from app.domains.identity.models.management_function import ManagementFunctionModel
from app.domains.identity.models.manager_user import ManagerUserModel, ManagerUserStatus
from app.domains.identity.models.permission import PermissionModel
from app.domains.identity.models.role import RoleModel
from app.domains.identity.models.role_permission import RolePermissionModel
from app.domains.identity.security import Argon2PasswordHasher
from app.main import create_app


ACTIONS = ("read", "create", "update")
TEST_LANGUAGE_CODES = ("zza", "aar", "abk", "ace")


def run() -> None:
    suffix = token_hex(4)
    function_id = f"func-{suffix}"
    owns_function = False
    role_id = f"role-{suffix}"
    user_id = f"user-{suffix}"
    permission_ids = {
        action: f"perm-{action[0]}{suffix}" for action in ACTIONS
    }
    email = f"language-{suffix}@test.invalid"
    password = token_urlsafe(24)
    language_id: str | None = None
    created_language_id: str | None = None
    test_language_code: str | None = None
    engine = create_engine(database_url, pool_pre_ping=True)

    def grant(action_name: str) -> None:
        with Session(engine) as session, session.begin():
            session.add(
                RolePermissionModel(
                    role_id=role_id,
                    permission_id=permission_ids[action_name],
                )
            )

    try:
        now = datetime.now(timezone.utc)
        with Session(engine) as session, session.begin():
            existing_function = session.scalar(
                select(ManagementFunctionModel.id).where(
                    ManagementFunctionModel.name == "Language Management"
                )
            )
            if existing_function is not None:
                function_id = existing_function
            else:
                owns_function = True

            existing_codes = set(
                session.scalars(
                    select(Language.language_code).where(
                        Language.language_code.in_(TEST_LANGUAGE_CODES)
                    )
                )
            )
            test_language_code = next(
                (code for code in TEST_LANGUAGE_CODES if code not in existing_codes),
                None,
            )
            if test_language_code is None:
                raise RuntimeError("isolated database has no free Language test code")

            actions = {
                action.name: action
                for action in session.scalars(
                    select(ActionModel).where(ActionModel.name.in_(ACTIONS))
                )
            }
            if set(actions) != set(ACTIONS):
                raise RuntimeError("isolated database lacks standard RBAC actions")

            if owns_function:
                session.add(
                    ManagementFunctionModel(
                        id=function_id,
                        name="Language Management",
                        description="Temporary Language full-stack test function",
                    )
                )
            session.add(
                RoleModel(
                    id=role_id,
                    name=f"Language Test Role {suffix}",
                    description="Temporary Language full-stack test role",
                    created_by=None,
                    last_updated_by=None,
                    created_at=now,
                    last_updated_at=now,
                )
            )
            session.flush()
            session.add(
                ManagerUserModel(
                    id=user_id,
                    role_id=role_id,
                    email=email,
                    password_hash=Argon2PasswordHasher().hash_password(password),
                    full_name="Language Full Stack Test",
                    user_status=ManagerUserStatus.ACTIVE,
                    created_at=now,
                    last_updated_at=now,
                    last_login_at=None,
                )
            )
            for action_name, permission_id in permission_ids.items():
                session.add(
                    PermissionModel(
                        id=permission_id,
                        function_id=function_id,
                        action_id=actions[action_name].id,
                    )
                )

        with TestClient(create_app()) as client:
            unauthorized = client.get("/api/v1/admin/catalog/languages")
            assert unauthorized.status_code == 401
            print("admin_without_token=401")

            login = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200
            assert login.json()["user"]["id"] == user_id
            print("login=200")
            headers = {
                "Authorization": f"Bearer {login.json()['access_token']}"
            }

            read_denied = client.get(
                "/api/v1/admin/catalog/languages", headers=headers
            )
            assert read_denied.status_code == 403
            grant("read")
            read_allowed = client.get(
                "/api/v1/admin/catalog/languages", headers=headers
            )
            assert read_allowed.status_code == 200
            assert [row["id"] for row in read_allowed.json()] == sorted(
                row["id"] for row in read_allowed.json()
            )
            print("read=403_then_200")

            payload = {
                "language_code": test_language_code,
                "language_name": f"Zaza Full Stack {suffix}",
                "language_status": "SUPPORTED",
            }
            create_denied = client.post(
                "/api/v1/admin/catalog/languages",
                headers=headers,
                json=payload,
            )
            assert create_denied.status_code == 403
            grant("create")
            create_allowed = client.post(
                "/api/v1/admin/catalog/languages",
                headers=headers,
                json=payload,
            )
            assert create_allowed.status_code == 201
            language_id = create_allowed.json()["id"]
            created_language_id = language_id

            duplicate = client.post(
                "/api/v1/admin/catalog/languages",
                headers=headers,
                json={
                    "language_code": test_language_code,
                    "language_name": f"Duplicate Full Stack {suffix}",
                    "language_status": "SUPPORTED",
                },
            )
            assert duplicate.status_code == 409

            public_supported = client.get("/api/v1/catalog/languages")
            assert public_supported.status_code == 200
            assert any(
                row["id"] == language_id for row in public_supported.json()
            )
            print("create=403_then_201")

            update_denied = client.patch(
                f"/api/v1/admin/catalog/languages/{language_id}",
                headers=headers,
                json={
                    "language_name": f"Zaza Full Stack Updated {suffix}",
                    "language_status": "UNSUPPORTED",
                },
            )
            assert update_denied.status_code == 403
            grant("update")
            update_allowed = client.patch(
                f"/api/v1/admin/catalog/languages/{language_id}",
                headers=headers,
                json={
                    "language_name": f"Zaza Full Stack Updated {suffix}",
                    "language_status": "UNSUPPORTED",
                },
            )
            assert update_allowed.status_code == 200
            assert update_allowed.json()["language_status"] == "UNSUPPORTED"
            public_unsupported = client.get("/api/v1/catalog/languages")
            assert public_unsupported.status_code == 200
            assert all(
                row["id"] != language_id for row in public_unsupported.json()
            )
            print("update=403_then_200")

            delete_not_supported = client.delete(
                f"/api/v1/admin/catalog/languages/{language_id}",
                headers=headers,
            )
            assert delete_not_supported.status_code == 405
            print("delete=405")
    finally:
        with Session(engine) as session, session.begin():
            if language_id is not None:
                session.execute(delete(Language).where(Language.id == language_id))
            session.execute(
                delete(RolePermissionModel).where(
                    RolePermissionModel.role_id == role_id
                )
            )
            session.execute(
                delete(ManagerUserModel).where(ManagerUserModel.id == user_id)
            )
            session.execute(
                delete(PermissionModel).where(
                    PermissionModel.id.in_(permission_ids.values())
                )
            )
            session.execute(delete(RoleModel).where(RoleModel.id == role_id))
            if owns_function:
                session.execute(
                    delete(ManagementFunctionModel).where(
                        ManagementFunctionModel.id == function_id
                    )
                )
        with Session(engine) as session:
            assert session.get(ManagerUserModel, user_id) is None
            assert session.get(RoleModel, role_id) is None
            if owns_function:
                assert session.get(ManagementFunctionModel, function_id) is None
            else:
                assert session.get(ManagementFunctionModel, function_id) is not None
            assert all(
                session.get(PermissionModel, permission_id) is None
                for permission_id in permission_ids.values()
            )
            if created_language_id is not None:
                assert session.get(Language, created_language_id) is None
        print("cleanup=ok")
        engine.dispose()


if __name__ == "__main__":
    run()
