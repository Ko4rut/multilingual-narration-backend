"""Safely convert legacy Language status ``active`` to ``SUPPORTED``.

The command is a dry-run unless ``--apply`` is supplied. It validates every
Language row before changing data and never rewrites statuses other than the
legacy value explicitly covered by this conversion.
"""

from __future__ import annotations

import argparse
from collections import Counter

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domains.catalog.utils import normalize_language_code


ALLOWED_STATUSES = {"active", "SUPPORTED", "UNSUPPORTED"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the conversion. Without this flag the command is read-only.",
    )
    parser.add_argument(
        "--expect-active-count",
        type=int,
        help="Required with --apply; abort unless this many legacy rows exist.",
    )
    args = parser.parse_args()
    if args.apply and args.expect_active_count is None:
        parser.error("--apply requires --expect-active-count")
    if args.expect_active_count is not None and args.expect_active_count < 0:
        parser.error("--expect-active-count must be non-negative")
    return args


def preflight(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    codes = Counter(row["language_code"] for row in rows)
    names = Counter(row["language_name"] for row in rows)

    for row in rows:
        row_errors: list[str] = []
        code = row["language_code"]
        name = row["language_name"]
        status = row["language_status"]
        try:
            if normalize_language_code(code) != code:
                row_errors.append("language_code is not normalized")
        except ValueError:
            row_errors.append("language_code is not ISO 639-1/2")
        if not name.strip() or name != name.strip():
            row_errors.append("language_name is empty or untrimmed")
        if status not in ALLOWED_STATUSES:
            row_errors.append(f"unexpected language_status {status!r}")
        if codes[code] > 1:
            row_errors.append("duplicate language_code")
        if names[name] > 1:
            row_errors.append("duplicate language_name")
        if row_errors:
            errors.append(f"{row['id']}: {', '.join(row_errors)}")
    return errors


def main() -> None:
    args = parse_args()
    engine = create_engine(
        get_settings().database_url.get_secret_value(), pool_pre_ping=True
    )
    try:
        with Session(engine) as session, session.begin():
            statement = text(
                "SELECT id, language_code, language_name, language_status "
                "FROM language ORDER BY id"
            )
            if args.apply:
                statement = text(f"{statement.text} FOR UPDATE")
            rows = [dict(row) for row in session.execute(statement).mappings()]
            errors = preflight(rows)
            if errors:
                raise RuntimeError("Language preflight failed:\n" + "\n".join(errors))

            status_counts = Counter(row["language_status"] for row in rows)
            active_count = status_counts["active"]
            print(f"Language status counts: {dict(sorted(status_counts.items()))}")
            print(f"Legacy rows eligible for conversion: {active_count}")

            if not args.apply:
                print("Dry-run complete; no data changed.")
                return
            if active_count != args.expect_active_count:
                raise RuntimeError(
                    "Expected "
                    f"{args.expect_active_count} active rows, found {active_count}"
                )

            result = session.execute(
                text(
                    "UPDATE language SET language_status = 'SUPPORTED' "
                    "WHERE language_status = 'active'"
                )
            )
            if result.rowcount != active_count:
                raise RuntimeError(
                    f"Expected to update {active_count} rows, updated {result.rowcount}"
                )
            print(f"Converted {result.rowcount} rows to SUPPORTED.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
