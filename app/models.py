"""SQLAlchemy models for the paste service."""

from datetime import datetime, timedelta

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Paste(Base):
    """Paste model for storing paste metadata."""

    __tablename__ = "pastes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paste_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delete_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    @property
    def is_expired(self) -> bool:
        """Check if the paste has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_image(self) -> bool:
        """Check if the paste is an image."""
        return self.content_type.startswith("image/")

    @property
    def is_markdown(self) -> bool:
        """Check if the paste is a markdown file."""
        return self.filename and self.filename.endswith(".md")
