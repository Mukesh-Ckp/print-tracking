"""
Idempotent seeding helpers run on application startup.

* ensure_default_admin: bootstraps a single super-admin from environment
  variables if no admin rows exist yet.
* ensure_default_printer: registers the configured shared office printer
  so the dashboard always shows it (even before the first print job arrives).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..auth.password import hash_password
from ..config import settings
from ..database.session import SessionLocal
from ..models.admin import Admin
from ..models.printer import Printer

logger = logging.getLogger(__name__)


def ensure_default_admin() -> None:
    """Create the bootstrap admin if the admins table is empty."""
    db: Session = SessionLocal()
    try:
        existing = db.query(Admin).count()
        if existing > 0:
            logger.info("Admin user already exists, skipping seed.")
            return

        admin = Admin(
            username=settings.DEFAULT_ADMIN_USERNAME,
            email=settings.DEFAULT_ADMIN_EMAIL,
            full_name=settings.DEFAULT_ADMIN_FULL_NAME,
            hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            is_active=True,
            is_superuser=True,
        )
        db.add(admin)
        db.commit()
        logger.warning(
            "Bootstrap admin created with username=%s. "
            "PLEASE CHANGE THE DEFAULT PASSWORD IMMEDIATELY.",
            settings.DEFAULT_ADMIN_USERNAME,
        )
    except Exception:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Failed to seed default admin.")
    finally:
        db.close()


def ensure_default_printer() -> None:
    """Register the configured shared office printer in the printers table."""
    db: Session = SessionLocal()
    try:
        existing = (
            db.query(Printer)
            .filter(Printer.name == settings.DEFAULT_PRINTER_NAME)
            .first()
        )
        if existing:
            return
        printer = Printer(
            name=settings.DEFAULT_PRINTER_NAME,
            ip_address=settings.DEFAULT_PRINTER_IP,
            model=settings.DEFAULT_PRINTER_NAME,
            location="Office",
            network=settings.DEFAULT_PRINTER_NETWORK,
            is_active=True,
        )
        db.add(printer)
        db.commit()
        logger.info("Registered default printer: %s", settings.DEFAULT_PRINTER_NAME)
    except Exception:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Failed to seed default printer.")
    finally:
        db.close()
