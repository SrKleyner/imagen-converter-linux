"""Input selection widget — drop zone plus Browse button (GS-3, IN-*)."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.formats import FormatRegistry


def expand_paths(paths: Iterable[str], registry: FormatRegistry) -> list[str]:
    """Expand files and folders into a de-duplicated list of supported images."""
    found: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        if candidate not in seen and registry.is_input_supported(Path(candidate).suffix):
            seen.add(candidate)
            found.append(candidate)

    for raw in paths:
        path = os.path.abspath(raw)
        if os.path.isdir(path):
            for root, dirs, names in os.walk(path):
                dirs.sort()
                for name in sorted(names):
                    add(os.path.join(root, name))
        elif os.path.isfile(path):
            add(path)
    return found


class InputWidget(QWidget):
    """Drag-and-drop zone with a Browse button.

    In single mode only one file is kept; in batch mode folders are expanded.
    """

    def __init__(
        self,
        registry: FormatRegistry,
        batch: bool,
        on_files_changed: Callable[[list[str]], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self._batch = batch
        self._on_files_changed = on_files_changed
        self._files: list[str] = []
        self.setAcceptDrops(True)

        hint = "Drop images or folders here" if batch else "Drop an image here"
        self._zone = QLabel(f"{hint}\nor use the button below")
        self._zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zone.setMinimumHeight(90)
        self._zone.setFrameShape(QLabel.Shape.StyledPanel)
        self._count = QLabel("No files selected")
        self._count.setWordWrap(True)

        browse = QPushButton("Add folder..." if batch else "Browse...")
        browse.clicked.connect(self._browse)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear)

        buttons = QHBoxLayout()
        buttons.addWidget(browse)
        buttons.addWidget(clear)
        layout = QVBoxLayout(self)
        layout.addWidget(self._zone)
        layout.addWidget(self._count)
        layout.addLayout(buttons)

    @property
    def files(self) -> list[str]:
        return list(self._files)

    def add_paths(self, paths: Iterable[str]) -> None:
        found = expand_paths(paths, self._registry)
        if not found:
            return
        if self._batch:
            known = set(self._files)
            self._files.extend(p for p in found if p not in known)
        else:
            self._files = found[:1]
        self._refresh()

    def clear(self) -> None:
        self._files = []
        self._refresh()

    def handle_mime(self, mime: QMimeData) -> bool:
        """Consume dropped local URLs; return False when nothing usable arrived."""
        if not mime.hasUrls():
            return False
        paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
        if not paths:
            return False
        self.add_paths(paths)
        return True

    # -- Qt events -------------------------------------------------------

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        if self.handle_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    # -- Internals -------------------------------------------------------

    def _browse(self) -> None:
        if self._batch:
            folder = QFileDialog.getExistingDirectory(self, "Select a folder")
            if folder:
                self.add_paths([folder])
        else:
            exts = " ".join(f"*{e}" for e in (".png", ".jpg", ".jpeg", ".webp", ".avif"))
            path, _ = QFileDialog.getOpenFileName(self, "Select an image", "", f"Images ({exts})")
            if path:
                self.add_paths([path])

    def _refresh(self) -> None:
        if not self._files:
            self._count.setText("No files selected")
        elif len(self._files) == 1:
            self._count.setText(self._files[0])
        else:
            self._count.setText(f"{len(self._files)} files selected")
        if self._on_files_changed:
            self._on_files_changed(self.files)
