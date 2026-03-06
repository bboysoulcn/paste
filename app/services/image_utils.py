"""Image utilities for extracting dimensions."""

from io import BytesIO

from PIL import Image


def get_image_dimensions(content: bytes) -> tuple[int, int] | None:
    """
    Extract width and height from image bytes.

    Supports: PNG, JPEG, GIF, WEBP

    Args:
        content: Image bytes

    Returns:
        Tuple of (width, height) or None if not an image or dimensions cannot be extracted
    """
    try:
        with Image.open(BytesIO(content)) as img:
            width, height = img.size
            return width, height
    except Exception:
        return None


def is_image_content(content: bytes) -> bool:
    """
    Check if content appears to be an image.

    Args:
        content: Content bytes

    Returns:
        True if content appears to be an image
    """
    try:
        with Image.open(BytesIO(content)) as img:
            img.verify()
            return True
    except Exception:
        return False
