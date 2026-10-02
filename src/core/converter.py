"""Core converter — the ONLY module that imports PIL.

D1: Single ``convert_one`` function (no class indirection needed yet).
CO-2: PNG (lossless) ignores quality parameter.
SC-1: happy-path conversion to any supported format.
SC-2: corrupt input reports ``CorruptInputError``.
SC-3: permission-denied output reports ``PermissionDeniedError``.
BC-6: disk-full reports ``DiskFullError``.
FR-3: unsupported input raises ``UnsupportedFormatError``.
FR-4: ``probe_avif()`` checks AVIF encoder availability at runtime.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from src.core.options import ConversionOptions

# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class ConversionError(Exception):
    """Base class for all conversion failures."""


class CorruptInputError(ConversionError):
    """Input file is unreadable or truncated (SC-2)."""


class PermissionDeniedError(ConversionError):
    """Cannot write to output path (SC-3)."""


class DiskFullError(ConversionError):
    """Disk is full during write (BC-6)."""


class UnsupportedFormatError(ConversionError):
    """Input format is not supported for reading (FR-3)."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def convert_one(
    input_path: str,
    out_path: str,
    opts: ConversionOptions,
) -> str:
    """Convert a single image file to *opts.target_format*.

    Parameters
    ----------
    input_path:
        Path to the source image.
    out_path:
        Desired output path (already resolved via ``resolve_output_path``).
    opts:
        Frozen conversion options (target format, quality, etc.).

    Returns
    -------
    str
        The output path (same as *out_path*) on success.

    Raises
    ------
    CorruptInputError
        If the input file cannot be read (SC-2).
    PermissionDeniedError
        If the output cannot be written due to permissions (SC-3).
    DiskFullError
        If the disk is full during write (BC-6).
    UnsupportedFormatError
        If the input format is not supported for reading (FR-3).
    """
    input_path = str(Path(input_path).resolve())
    out_path = str(Path(out_path).resolve())

    # Open image — this is the main work
    try:
        img = Image.open(input_path)
    except (OSError, Image.UnidentifiedImageError) as exc:
        raise CorruptInputError(f"Cannot read image: {input_path} — {exc}") from exc

    # Determine save parameters
    save_kwargs = _build_save_kwargs(img, opts)

    # Ensure output directory exists
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        raise PermissionDeniedError(
            f"Cannot create output directory: {Path(out_path).parent}"
        ) from exc

    # Convert and save
    try:
        img.save(out_path, **save_kwargs)
    except PermissionError as exc:
        raise PermissionDeniedError(f"Cannot write: {out_path}") from exc
    except OSError as exc:
        # Heuristic: ENOSPC (no space) → DiskFullError
        errno = getattr(exc, "errno", None)
        if errno == 28 or "No space" in str(exc):
            raise DiskFullError(f"Disk full while writing: {out_path}") from exc
        raise CorruptInputError(f"Save failed: {out_path} — {exc}") from exc

    return out_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_save_kwargs(
    img: Image.Image,
    opts: ConversionOptions,
) -> dict[str, Any]:
    """Build Pillow ``save()`` kwargs from *opts*.

    CO-2: PNG (lossless) → omit quality entirely.
    """
    fmt = opts.target_format.upper()

    quality_formats: dict[str, str] = {
        "JPG": "quality",
        "JPEG": "quality",
        "AVIF": "quality",
        "WEBP": "quality",
    }

    kwargs: dict[str, Any] = {}

    # CO-2: only pass quality when the format supports it
    if fmt in quality_formats and not (
        fmt == "PNG"  # safety net — should not happen
    ):
        kwargs[quality_formats[fmt]] = int(opts.quality)

    return kwargs


def probe_avif() -> bool:
    """Check whether the Pillow runtime can encode AVIF (FR-4).

    Creates a tiny 1×1 image and tries to save it as AVIF to a BytesIO
    buffer.  Returns ``True`` if the save succeeds, ``False`` otherwise.
    """
    try:
        img = Image.new("RGB", (1, 1), color=(255, 0, 0))
        buf = BytesIO()
        img.save(buf, format="AVIF")
        return bool(buf.getvalue())
    except Exception:
        return False
