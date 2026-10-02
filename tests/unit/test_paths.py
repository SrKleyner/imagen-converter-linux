"""Tests for src.utils.paths — resolve_output_path."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.utils.paths import resolve_output_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dir() -> str:
    with tempfile.TemporaryDirectory() as d:
        yield d


# ---------------------------------------------------------------------------
# CO-3: _converted suffix
# ---------------------------------------------------------------------------


class TestConvertedSuffix:
    """CO-3: target exists → ``_converted`` suffix."""

    def test_no_conflict(self, tmp_dir: str) -> None:
        out = resolve_output_path("photo.jpg", ".png", tmp_dir)
        assert out == os.path.join(tmp_dir, "photo.png")

    def test_conflict_adds_converted(self, tmp_dir: str) -> None:
        # Create a file that would clash
        Path(os.path.join(tmp_dir, "photo.png")).write_text("")
        out = resolve_output_path("photo.jpg", ".png", tmp_dir)
        assert out == os.path.join(tmp_dir, "photo_converted.png")


# ---------------------------------------------------------------------------
# CO-4: sequential suffix
# ---------------------------------------------------------------------------


class TestSequentialSuffix:
    """CO-4: suffixed name also exists → ``_1``, ``_2``, ..."""

    def test_seq_1(self, tmp_dir: str) -> None:
        Path(os.path.join(tmp_dir, "photo.png")).write_text("")
        Path(os.path.join(tmp_dir, "photo_converted.png")).write_text("")
        out = resolve_output_path("photo.jpg", ".png", tmp_dir)
        assert out == os.path.join(tmp_dir, "photo_converted_1.png")

    def test_seq_2(self, tmp_dir: str) -> None:
        Path(os.path.join(tmp_dir, "photo.png")).write_text("")
        Path(os.path.join(tmp_dir, "photo_converted.png")).write_text("")
        Path(os.path.join(tmp_dir, "photo_converted_1.png")).write_text("")
        out = resolve_output_path("photo.jpg", ".png", tmp_dir)
        assert out == os.path.join(tmp_dir, "photo_converted_2.png")

    def test_seq_many(self, tmp_dir: str) -> None:
        Path(os.path.join(tmp_dir, "x.png")).write_text("")
        Path(os.path.join(tmp_dir, "x_converted.png")).write_text("")
        for i in range(1, 6):
            Path(os.path.join(tmp_dir, f"x_converted_{i}.png")).write_text("")
        out = resolve_output_path("x.jpg", ".png", tmp_dir)
        assert out == os.path.join(tmp_dir, "x_converted_6.png")


# ---------------------------------------------------------------------------
# BC-2: single-folder mode
# ---------------------------------------------------------------------------


class TestSingleMode:
    """BC-2: all outputs land in one folder."""

    def test_nested_input_flat_output(self, tmp_dir: str) -> None:
        """Even if input path has nested dirs, output lands in output_dir."""
        out = resolve_output_path(
            os.path.join("a", "b", "photo.jpg"),
            ".png",
            tmp_dir,
            output_mode="single",
        )
        expected = os.path.join(tmp_dir, "photo.png")
        assert out == expected


# ---------------------------------------------------------------------------
# BC-3: mirror mode
# ---------------------------------------------------------------------------


class TestMirrorMode:
    """BC-3: output tree mirrors input tree."""

    def test_mirror_preserves_structure(self, tmp_dir: str) -> None:
        common = os.path.join(tmp_dir, "inputs")
        os.makedirs(os.path.join(common, "sub"))
        in_path = os.path.join(common, "sub", "photo.jpg")
        out_dir = os.path.join(tmp_dir, "outputs")

        out = resolve_output_path(
            in_path, ".png", out_dir, output_mode="mirror", common_root=common
        )
        expected = os.path.join(out_dir, "sub", "photo.png")
        assert out == expected

    def test_mirror_creates_subdirs(self, tmp_dir: str) -> None:
        common = os.path.join(tmp_dir, "src")
        os.makedirs(os.path.join(common, "nested", "deep"))
        in_path = os.path.join(common, "nested", "deep", "img.jpg")
        out_dir = os.path.join(tmp_dir, "dst")

        out = resolve_output_path(
            in_path, ".webp", out_dir, output_mode="mirror", common_root=common
        )
        expected = os.path.join(out_dir, "nested", "deep", "img.webp")
        assert out == expected
        # Verify directory was created
        assert os.path.isdir(os.path.dirname(out))


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_filename_with_multiple_dots(self, tmp_dir: str) -> None:
        out = resolve_output_path("my.photo.tar.gz.jpg", ".avif", tmp_dir)
        assert out == os.path.join(tmp_dir, "my.photo.tar.gz.avif")

    def test_uppercase_input_ext(self, tmp_dir: str) -> None:
        out = resolve_output_path("PHOTO.JPG", ".png", tmp_dir)
        assert out == os.path.join(tmp_dir, "PHOTO.png")
