"""
Reset an admin password in the local database.

This is meant for LOCAL development when you forgot the seeded password.

Usage:
  # from backend/
  py scripts/reset_admin_password.py --username admin --password "Admin@123"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

# Ensure `backend/` is on sys.path even when running from `scripts/`.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.auth.password import hash_password
from app.database.session import SessionLocal
from app.models.admin import Admin


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset an admin password.")
    parser.add_argument("--username", default="admin", help="Admin username to reset.")
    parser.add_argument(
        "--password",
        default="Admin@123",
        help="New password to set (default: Admin@123).",
    )
    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.username == args.username).first()
        if not admin:
            raise SystemExit(f"Admin not found: {args.username!r}")
        admin.hashed_password = hash_password(args.password)
        db.commit()
        print(f"OK: password reset for username={admin.username!r}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

