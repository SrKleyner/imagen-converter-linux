"""Conversion options — frozen dataclass holding user choices."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConversionOptions:
    """Immutable conversion parameters set by the GUI before execution.

    CO-1: quality slider 1..100, default 85.
    CO-2: quality ignored for lossless formats (handled by convert_one).
    """

    target_format: str  # canonical id from FormatRegistry (e.g. "JPG", "AVIF")
    quality: int = 85  # 1–100; ignored when not supported by the target format
    output_dir: str = ""
    output_mode: str = "single"  # "single" | "mirror"
    common_root: str | None = None  # base directory for "mirror" mode

    def __post_init__(self) -> None:
        if not (1 <= self.quality <= 100):
            raise ValueError(f"quality must be 1–100, got {self.quality}")
        if self.output_mode not in ("single", "mirror"):
            raise ValueError(
                f"output_mode must be 'single' or 'mirror', got {self.output_mode!r}"
            )
