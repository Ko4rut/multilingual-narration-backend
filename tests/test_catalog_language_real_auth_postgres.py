import os
import subprocess
import sys
from pathlib import Path
from secrets import token_hex

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL must point to an isolated PostgreSQL database",
)
def test_real_login_jwt_rbac_and_language_admin_on_postgresql():
    root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root)
    command = [
        sys.executable,
        str(root / "tests" / "_language_real_auth_harness.py"),
    ]

    def run_harness():
        result = subprocess.run(
            command,
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    # Cover both ownership paths: harness-created function and a pre-provisioned
    # Language Management function that the harness must preserve.
    run_harness()

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    function_id = f"func-{token_hex(4)}"
    owns_function = False
    try:
        with engine.begin() as connection:
            existing_id = connection.execute(
                text(
                    "SELECT id FROM management_function "
                    "WHERE name = 'Language Management'"
                )
            ).scalar_one_or_none()
            if existing_id is None:
                connection.execute(
                    text(
                        "INSERT INTO management_function (id, name, description) "
                        "VALUES (:id, 'Language Management', :description)"
                    ),
                    {
                        "id": function_id,
                        "description": "Temporary pre-provisioned test function",
                    },
                )
                owns_function = True
            else:
                function_id = existing_id
        run_harness()
    finally:
        if owns_function:
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM management_function WHERE id = :id"),
                    {"id": function_id},
                )
        engine.dispose()
