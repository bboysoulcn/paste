"""Paste service business logic."""

import secrets
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Paste
from app.services.image_utils import get_image_dimensions

settings = get_settings()


def generate_id(length: int | None = None) -> str:
    """
    Generate a random ID for a paste.

    Args:
        length: Length of the ID to generate (defaults to settings.id_length)

    Returns:
        Random string ID
    """
    if length is None:
        length = settings.id_length
    return secrets.token_urlsafe(length)[:length]


def generate_delete_token() -> str:
    """
    Generate a random deletion token.

    Returns:
        Random token string
    """
    return secrets.token_urlsafe(32)


def detect_content_type(content: bytes, filename: str | None = None) -> str:
    """
    Detect content type from content and optional filename.

    Args:
        content: Content bytes
        filename: Optional filename with extension

    Returns:
        MIME type string
    """
    # Check if it's an image first
    dimensions = get_image_dimensions(content)
    if dimensions:
        # Try to detect specific image type from content
        if content.startswith(b'\x89PNG\r\n\x1a\n'):
            return "image/png"
        elif content.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        elif content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
            return "image/gif"
        elif content.startswith(b'RIFF') and b'WEBP' in content[:12]:
            return "image/webp"
        return "image/png"

    # Check filename extension
    if filename:
        ext = filename.rsplit('.', 1)[-1].lower()
        content_types = {
            'md': 'text/markdown',
            'txt': 'text/plain',
            'html': 'text/html',
            'css': 'text/css',
            'js': 'application/javascript',
            'json': 'application/json',
            'xml': 'application/xml',
            'py': 'text/x-python',
            'sh': 'text/x-shellscript',
            'yaml': 'text/x-yaml',
            'yml': 'text/x-yaml',
        }
        if ext in content_types:
            return content_types[ext]

    # Default to text/plain
    return "text/plain"


async def save_paste(
    db: AsyncSession,
    content: bytes,
    filename: str | None = None,
    paste_id: str | None = None,
) -> Paste:
    """
    Save a paste to storage and database.

    Args:
        db: Database session
        content: Content bytes to save
        filename: Optional filename
        paste_id: Optional specific paste ID (if not provided, generates random)

    Returns:
        Created Paste object
    """
    if paste_id is None:
        paste_id = generate_id()

    # Generate unique ID if collision occurs
    existing = await get_paste(db, paste_id)
    while existing is not None:
        paste_id = generate_id()
        existing = await get_paste(db, paste_id)

    delete_token = generate_delete_token()
    content_type = detect_content_type(content, filename)

    # Detect image dimensions if applicable
    image_width = None
    image_height = None
    if content_type.startswith("image/"):
        dimensions = get_image_dimensions(content)
        if dimensions:
            image_width, image_height = dimensions

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(hours=settings.expiration_hours)

    # Save to file system
    storage_dir = Path(settings.storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)

    storage_filename = f"{paste_id}_{filename}" if filename else paste_id
    storage_path = storage_dir / storage_filename

    with open(storage_path, 'wb') as f:
        f.write(content)

    # Create database record
    paste = Paste(
        paste_id=paste_id,
        filename=filename,
        content_type=content_type,
        file_size=len(content),
        image_width=image_width,
        image_height=image_height,
        delete_token=delete_token,
        expires_at=expires_at,
        storage_path=str(storage_path),
    )

    db.add(paste)
    await db.commit()
    await db.refresh(paste)

    return paste


async def get_paste(db: AsyncSession, paste_id: str) -> Paste | None:
    """
    Retrieve a paste by ID.

    Args:
        db: Database session
        paste_id: Paste ID to retrieve

    Returns:
        Paste object or None if not found
    """
    result = await db.execute(select(Paste).where(Paste.paste_id == paste_id))
    return result.scalar_one_or_none()


async def delete_paste(db: AsyncSession, paste_id: str, delete_token: str) -> bool:
    """
    Delete a paste by ID and token.

    Args:
        db: Database session
        paste_id: Paste ID to delete
        delete_token: Deletion token for validation

    Returns:
        True if deleted, False if not found or invalid token
    """
    paste = await get_paste(db, paste_id)
    if paste is None:
        return False

    if paste.delete_token != delete_token:
        return False

    # Delete file from filesystem
    try:
        storage_path = Path(paste.storage_path)
        if storage_path.exists():
            storage_path.unlink()
    except Exception:
        pass  # Continue with database deletion even if file deletion fails

    # Delete from database
    await db.delete(paste)
    await db.commit()

    return True


async def clean_expired(db: AsyncSession) -> int:
    """
    Remove expired pastes from database and filesystem.

    Args:
        db: Database session

    Returns:
        Number of pastes cleaned
    """
    now = datetime.utcnow()
    result = await db.execute(
        select(Paste).where(Paste.expires_at < now)
    )
    expired_pastes = result.scalars().all()

    count = 0
    for paste in expired_pastes:
        try:
            # Delete file from filesystem
            storage_path = Path(paste.storage_path)
            if storage_path.exists():
                storage_path.unlink()

            # Delete from database
            await db.delete(paste)
            count += 1
        except Exception:
            pass  # Skip this paste if deletion fails

    await db.commit()
    return count


def read_paste_content(paste: Paste) -> bytes:
    """
    Read content from paste's storage path.

    Args:
        paste: Paste object

    Returns:
        Content bytes
    """
    storage_path = Path(paste.storage_path)
    with open(storage_path, 'rb') as f:
        return f.read()
