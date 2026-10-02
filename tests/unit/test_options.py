"""Tests for src.core.options — ConversionOptions."""

from __future__ import annotations

import pytest

from src.core.options import ConversionOptions


class TestConversionOptions:
    """CO-1: quality slider defaults to 85."""

    def test_defaults(self) -> None:
        opts = ConversionOptions(target_format="JPG")
        assert opts.quality == 85
        assert opts.output_dir == ""
        assert opts.output_mode == "single"
        assert opts.common_root is None

    def test_quality_range(self) -> None:
        for q in (1, 50, 85, 100):
            opts = ConversionOptions(target_format="PNG", quality=q)
            assert opts.quality == q

    def test_quality_out_of_range(self) -> None:
        for bad in (0, 101, -5, 200):
            with pytest.raises(ValueError, match="quality"):
                ConversionOptions(target_format="JPG", quality=bad)

    def test_frozen(self) -> None:
        opts = ConversionOptions(target_format="WEBP")
        with pytest.raises(Exception):
            opts.quality = 90  # type: ignore[misc]

    def test_output_mode_invalid(self) -> None:
        with pytest.raises(ValueError, match="output_mode"):
            ConversionOptions(target_format="JPG", output_mode="invalid")

    def test_output_mode_single(self) -> None:
        opts = ConversionOptions(target_format="JPG", output_mode="single")
        assert opts.output_mode == "single"

    def test_output_mode_mirror(self) -> None:
        opts = ConversionOptions(target_format="JPG", output_mode="mirror", common_root="/a")
        assert opts.output_mode == "mirror"
        assert opts.common_root == "/a"

    def test_common_root_default(self) -> None:
        opts = ConversionOptions(target_format="JPG")
        assert opts.common_root is None
