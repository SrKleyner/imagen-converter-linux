"""Format registry — single source of truth for output formats."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormatInfo:
    """Immutable descriptor for a supported output format."""

    canonical_id: str  # e.g. "JPG", "PNG", "AVIF", "WEBP"
    label: str  # e.g. "JPG", "PNG", "AVIF", "WebP"
    ext: str  # e.g. ".jpg", ".png", ".avif", ".webp"
    pil_format: str  # e.g. "JPEG", "PNG", "AVIF", "WEBP"
    supports_quality: bool
    supports_lossless: bool


# Built-in formats (always available)
_BUILTIN_FORMATS: dict[str, FormatInfo] = {
    "JPG": FormatInfo(
        canonical_id="JPG",
        label="JPG",
        ext=".jpg",
        pil_format="JPEG",
        supports_quality=True,
        supports_lossless=False,
    ),
    "WEBP": FormatInfo(
        canonical_id="WEBP",
        label="WebP",
        ext=".webp",
        pil_format="WEBP",
        supports_quality=True,
        supports_lossless=True,
    ),
    "PNG": FormatInfo(
        canonical_id="PNG",
        label="PNG",
        ext=".png",
        pil_format="PNG",
        supports_quality=False,
        supports_lossless=True,
    ),
}

_AVIF_FORMAT = FormatInfo(
    canonical_id="AVIF",
    label="AVIF",
    ext=".avif",
    pil_format="AVIF",
    supports_quality=True,
    supports_lossless=False,
)

# Extension → canonical_id map (normalization)
_EXT_TO_CANONICAL: dict[str, str] = {
    ".jpg": "JPG",
    ".jpeg": "JPG",
    ".jpe": "JPG",
    ".jfif": "JPG",
    ".png": "PNG",
    ".apng": "PNG",
    ".webp": "WEBP",
    ".avif": "AVIF",
    ".avifs": "AVIF",
}

# Canonical IDs that map to input formats we can READ
_INPUT_FORMATS = {"JPG", "PNG", "WEBP", "AVIF"}


class FormatRegistry:
    """Single source of truth for format metadata and alias resolution.

    FR-1: four supported output formats in UI dropdown.
    FR-2: normalizes ``.jpeg`` → ``JPG``.
    FR-3: unsupported input returns ``None``.
    FR-4: AVIF is omitted when the runtime encoder is unavailable.
    """

    def __init__(self, avif_available: bool = True) -> None:
        self._avif_available = avif_available

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_available(self) -> list[FormatInfo]:
        """Return available output formats for UI dropdowns.

        Returns 4 formats when AVIF is enabled, 3 otherwise (FR-1, FR-4).
        """
        formats: list[FormatInfo] = [
            _BUILTIN_FORMATS["JPG"],
            _BUILTIN_FORMATS["WEBP"],
            _BUILTIN_FORMATS["PNG"],
        ]
        if self._avif_available:
            formats.append(_AVIF_FORMAT)
        return formats

    def normalize_input_ext(self, ext: str) -> str | None:
        """Map a file extension to its canonical format id (FR-2).

        Returns ``None`` for unsupported formats (FR-3).
        Comparison is **case-insensitive**.
        """
        return _EXT_TO_CANONICAL.get(ext.lower())

    def get(self, canonical_id: str) -> FormatInfo | None:
        """Look up a ``FormatInfo`` by canonical id."""
        all_formats = {f.canonical_id: f for f in self.list_available()}
        return all_formats.get(canonical_id.upper())

    def is_input_supported(self, ext: str) -> bool:
        """Return ``True`` if *ext* maps to a format Pillow can read."""
        canonical = self.normalize_input_ext(ext)
        return canonical is not None and canonical in _INPUT_FORMATS

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def avif_available(self) -> bool:
        return self._avif_available
