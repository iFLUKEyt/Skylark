"""Fallback imghdr module packaged for pip installation.

This module mirrors the minimal `what()` implementation added at repo root
so Streamlit (imported before the app code) can import `imghdr` successfully.
"""
from typing import Optional

def _matches(header: bytes, sig: bytes) -> bool:
    return header.startswith(sig)

def what(file, h: Optional[bytes] = None) -> Optional[str]:
    header = h
    if header is None:
        try:
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
    if _matches(header, b"II*\x00") or _matches(header, b"MM\x00*"):
        return 'tiff'
    if len(header) >= 12 and header[0:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'webp'
    return None
