"""Image preprocessing. Uses Pillow but exposes only bytes in/bytes out so
callers never depend on the imaging library directly."""
from __future__ import annotations

import io

from PIL import Image, ImageOps

from app.domain.errors import ImageProcessingError


class ImagePreprocessor:
    """Resizes, strips EXIF, normalizes orientation, and re-encodes as JPEG."""

    def __init__(self, max_dimension_px: int, jpeg_quality: int = 85) -> None:
        self._max_dimension_px = max_dimension_px
        self._jpeg_quality = jpeg_quality

    def process(self, image_bytes: bytes, source_path: str) -> tuple[bytes, str]:
        """Returns (processed_jpeg_bytes, mime_type). Raises
        ImageProcessingError on any decode/encode failure."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # normalize orientation using EXIF, then drop all EXIF data
                img = ImageOps.exif_transpose(img)
                if img is None:
                    raise ImageProcessingError(source_path, "empty image after orientation fix")

                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")

                img.thumbnail(
                    (self._max_dimension_px, self._max_dimension_px),
                    Image.Resampling.LANCZOS,
                )

                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=self._jpeg_quality, exif=b"")
                return buffer.getvalue(), "image/jpeg"
        except ImageProcessingError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize all decode errors
            raise ImageProcessingError(source_path, str(exc)) from exc
