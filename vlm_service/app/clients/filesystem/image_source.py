"""Filesystem adapter implementing `domain.interfaces.ImageSource`.

Recursively discovers image files under a site's directory and reads raw
bytes. Preprocessing (resize/strip EXIF/etc.) is handled separately in
`services.analysis.image_processor` so this adapter stays a thin I/O shim.
"""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Sequence

from app.domain.models import ImageRef


class FilesystemImageSource:
    def __init__(self, allowed_extensions: tuple[str, ...], min_size_bytes: int) -> None:
        self._allowed_extensions = {ext.lower() for ext in allowed_extensions}
        self._min_size_bytes = min_size_bytes

    def discover(self, site_id: str, site_root: str) -> Sequence[ImageRef]:
        root = Path(site_root)
        if not root.is_dir():
            return []

        refs: list[ImageRef] = []
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                full_path = Path(dirpath) / filename
                if full_path.suffix.lower() not in self._allowed_extensions:
                    continue
                try:
                    size = full_path.stat().st_size
                except OSError:
                    continue
                if size < self._min_size_bytes:
                    continue
                refs.append(
                    ImageRef(
                        site_id=site_id,
                        path=PurePosixPath(full_path.as_posix()),
                        size_bytes=size,
                    )
                )
        return refs

    def read_bytes(self, image: ImageRef) -> bytes:
        return Path(image.path).read_bytes()
