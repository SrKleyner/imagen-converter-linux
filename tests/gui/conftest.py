"""GUI test fixtures — headless Qt via the offscreen platform."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.core.formats import FormatRegistry  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def registry():
    return FormatRegistry(avif_available=True)


@pytest.fixture
def no_avif_registry():
    return FormatRegistry(avif_available=False)
