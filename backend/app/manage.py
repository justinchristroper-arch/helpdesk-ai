"""Explicit management commands; never creates an administrator automatically."""
import argparse
import getpass
from pathlib import Path

from sqlalchemy import select

from app.auth import passwords
from app.db import Session
from app.models import User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create-user"])
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=["employee", "admin"], default="employee")
    args = parser.parse_args()
    password = getpass.getpass("Password (minimum 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password is too short.")
    with Session() as db:
        if db.scalar(select(User).where(User.email == args.email.lower().strip())):
            raise SystemExit("User already exists.")
        db.add(User(email=args.email.lower().strip(), role=args.role, password_hash=passwords.hash(password)))
        db.commit()
    print("User created.")


if __name__ == "__main__":
    main()
