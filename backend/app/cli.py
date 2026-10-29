import argparse
import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import hash_password


def create_admin(username: str, full_name: str) -> int:
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)) is not None:
            print(f"Error: user '{username}' already exists.", file=sys.stderr)
            return 1

        password = getpass.getpass("Password: ")
        confirmation = getpass.getpass("Repeat password: ")
        if not password:
            print("Error: password cannot be empty.", file=sys.stderr)
            return 1
        if password != confirmation:
            print("Error: passwords do not match.", file=sys.stderr)
            return 1

        db.add(
            User(
                username=username,
                full_name=full_name,
                password_hash=hash_password(password),
                role="admin",
                is_active=True,
            )
        )
        db.commit()

    print(f"Admin '{username}' created.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subparsers.add_parser("create-admin", help="Create an administrator user")
    create_admin_parser.add_argument("--username", required=True)
    create_admin_parser.add_argument("--full-name", required=True)

    args = parser.parse_args(argv)
    if args.command == "create-admin":
        return create_admin(args.username, args.full_name)
    return 1


if __name__ == "__main__":
    sys.exit(main())
