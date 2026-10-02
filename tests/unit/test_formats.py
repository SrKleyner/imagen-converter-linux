"""Tests for src.core.formats — FormatRegistry."""

from __future__ import annotations

import pytest

from src.core.formats import FormatInfo, FormatRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> FormatRegistry:
    """Registry with AVIF available (default)."""
    return FormatRegistry(avif_available=True)


@pytest.fixture
def registry_no_avif() -> FormatRegistry:
    """Registry without AVIF (FR-4)."""
    return FormatRegistry(avif_available=False)


# ---------------------------------------------------------------------------
# FormatInfo
# ---------------------------------------------------------------------------


class TestFormatInfo:
    def test_frozen(self) -> None:
        info = FormatInfo("A", "A", ".a", "A", True, False)
        with pytest.raises(Exception):
            info.canonical_id = "B"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FR-1: supported output formats in dropdown
# ---------------------------------------------------------------------------


class TestListAvailable:
    """FR-1: four formats when AVIF is present."""

    def test_returns_four_formats(self, registry: FormatRegistry) -> None:
        result = registry.list_available()
        assert len(result) == 4

    def test_returns_three_without_avif(self, registry_no_avif: FormatRegistry) -> None:
        result = registry_no_avif.list_available()
        assert len(result) == 3
        ids = {f.canonical_id for f in result}
        assert ids == {"JPG", "WEBP", "PNG"}

    def test_all_have_unique_canonical_ids(self, registry: FormatRegistry) -> None:
        result = registry.list_available()
        ids = [f.canonical_id for f in result]
        assert len(ids) == len(set(ids))

    def test_all_have_valid_pil_format(self, registry: FormatRegistry) -> None:
        for f in registry.list_available():
            assert f.pil_format in ("JPEG", "PNG", "AVIF", "WEBP")


# ---------------------------------------------------------------------------
# FR-2: JPG/JPEG alias normalisation
# ---------------------------------------------------------------------------


class TestNormalizeInputExt:
    """FR-2: ``.jpeg`` and ``.jpg`` resolve to ``JPG``."""

    @pytest.mark.parametrize(
        ("ext", "expected"),
        [
            (".jpg", "JPG"),
            (".jpeg", "JPG"),
            (".JPG", "JPG"),
            (".JpEg", "JPG"),
            (".png", "PNG"),
            (".webp", "WEBP"),
            (".avif", "AVIF"),
        ],
    )
    def test_known_extensions(self, registry: FormatRegistry, ext: str, expected: str) -> None:
        assert registry.normalize_input_ext(ext) == expected

    @pytest.mark.parametrize("ext", [".bmp", ".gif", ".tiff", ".svg", ".pdf", ""])
    def test_unknown_returns_none(self, registry: FormatRegistry, ext: str) -> None:
        assert registry.normalize_input_ext(ext) is None


# ---------------------------------------------------------------------------
# FR-3: unsupported input
# ---------------------------------------------------------------------------


class TestIsInputSupported:
    """FR-3: unsupported formats are rejected."""

    def test_supported_formats(self, registry: FormatRegistry) -> None:
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
            assert registry.is_input_supported(ext) is True, f"{ext} should be supported"

    def test_unsupported_format(self, registry: FormatRegistry) -> None:
        for ext in (".bmp", ".gif", ".tiff"):
            assert registry.is_input_supported(ext) is False, f"{ext} should NOT be supported"


# ---------------------------------------------------------------------------
# FR-4: AVIF runtime probe
# ---------------------------------------------------------------------------


class TestAvifProbe:
    """FR-4: AVIF is omitted when encoder unavailable."""

    def test_avif_present_by_default(self, registry: FormatRegistry) -> None:
        ids = {f.canonical_id for f in registry.list_available()}
        assert "AVIF" in ids

    def test_avif_absent_when_disabled(self, registry_no_avif: FormatRegistry) -> None:
        ids = {f.canonical_id for f in registry_no_avif.list_available()}
        assert "AVIF" not in ids


# ---------------------------------------------------------------------------
# Registry.get
# ---------------------------------------------------------------------------


class TestGet:
    def test_get_valid(self, registry: FormatRegistry) -> None:
        info = registry.get("JPG")
        assert info is not None
        assert info.canonical_id == "JPG"

    def test_get_case_insensitive(self, registry: FormatRegistry) -> None:
        info = registry.get("png")
        assert info is not None
        assert info.canonical_id == "PNG"

    def test_get_missing(self, registry: FormatRegistry) -> None:
        assert registry.get("BMP") is None
