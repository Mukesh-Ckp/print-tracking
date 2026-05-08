"""User profile mapping and print-limit configuration."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database.session import Base


class UserProfile(Base):
    """
    Maps raw spooler usernames to admin-curated display names and limits.

    Example:
      raw_username = "admin-pc\\john"
      display_name = "John Doe (Finance)"
      print_limit = 200
    """

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    raw_username: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Number of print jobs allowed; if null, unlimited.
    print_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserProfile raw={self.raw_username!r} display={self.display_name!r} limit={self.print_limit}>"

