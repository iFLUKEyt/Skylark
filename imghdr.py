"""Lightweight fallback for the removed/missing `imghdr` stdlib module.

This implements a minimal `what()` function used by libraries like
Streamlit to detect common image types by header bytes. It avoids adding
extra dependencies so the app can run in environments where the stdlib
`imghdr` module is missing (e.g., some Python 3.13 installs).

Supported return values: 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'
"""
from __future__ import annotations
from typing import Optional

def _matches(header: bytes, sig: bytes) -> bool:
    return header.startswith(sig)

def what(file, h: Optional[bytes] = None) -> Optional[str]:
    # If caller passed header bytes, use them; otherwise read from file
    header = h
    if header is None:
        try:
            # file may be a path or a file-like object
            if hasattr(file, 'read'):
                pos = file.tell() if hasattr(file, 'tell') else None
                header = file.read(32)
                if pos is not None:
                    try:
                        file.seek(pos)
                    except Exception:
                        pass
            else:
                with open(file, 'rb') as f:
                    header = f.read(32)
        except Exception:
            return None
    # Ensure we have bytes
    if not header:
        return None

    if _matches(header, b"\xFF\xD8\xFF"):
        return 'jpeg'
    if _matches(header, b"\x89PNG\r\n\x1a\n"):
        return 'png'
    if _matches(header, b"GIF87a") or _matches(header, b"GIF89a"):
        return 'gif'
    if _matches(header, b"BM"):
        return 'bmp'
    # TIFF can be little or big endian markers
    if _matches(header, b"II*\x00") or _matches(header, b"MM\x00*"):
        return 'tiff'
    # WebP has RIFF header with 'WEBP' at offset 8
    if len(header) >= 12 and header[0:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'webp'

    return None
