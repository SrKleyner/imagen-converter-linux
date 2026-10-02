"""Conversion options widget — format, quality, output folder and mode (CO-*)."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QWidget,
)

from src.core.formats import FormatRegistry
from src.core.options import ConversionOptions

_MODES = (("single", "Single folder"), ("mirror", "Mirror structure"))


class OptionsWidget(QWidget):
    """Collects user choices and builds a ``ConversionOptions``."""

    changed = Signal()

    def __init__(self, registry: FormatRegistry, batch: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._registry = registry
        self._formats = registry.list_available()

        self._format = QComboBox()
        for info in self._formats:
            self._format.addItem(info.label, info.canonical_id)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(1, 100)
        self._slider.setValue(85)
        self._value_label = QLabel("85")
        self._value_label.setMinimumWidth(28)
        quality_row = QHBoxLayout()
        quality_row.addWidget(self._slider)
        quality_row.addWidget(self._value_label)

        self._output = QLineEdit()
        self._output.setPlaceholderText("Output folder")
        pick = QPushButton("Choose...")
        pick.clicked.connect(self._pick_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self._output)
        output_row.addWidget(pick)

        self._mode = QComboBox()
        for mode_id, label in _MODES:
            self._mode.addItem(label, mode_id)

        form = QFormLayout(self)
        form.addRow("Format", self._format)
        form.addRow("Quality", quality_row)
        form.addRow("Output", output_row)
        self._mode_label = QLabel("Layout")
        form.addRow(self._mode_label, self._mode)
        self._mode.setVisible(batch)
        self._mode_label.setVisible(batch)
        self._batch = batch

        self._format.currentIndexChanged.connect(self._on_format_changed)
        self._slider.valueChanged.connect(self._on_quality_changed)
        self._output.textChanged.connect(lambda _t: self.changed.emit())
        self._mode.currentIndexChanged.connect(lambda _i: self.changed.emit())
        self._update_quality_enabled()

    # -- Accessors -------------------------------------------------------

    @property
    def format_ids(self) -> list[str]:
        return [self._format.itemData(i) for i in range(self._format.count())]

    @property
    def selected_format_id(self) -> str:
        return self._format.currentData()

    @property
    def quality(self) -> int:
        return self._slider.value()

    @quality.setter
    def quality(self, value: int) -> None:
        self._slider.setValue(value)

    @property
    def quality_enabled(self) -> bool:
        return self._slider.isEnabled()

    @property
    def output_dir(self) -> str:
        return self._output.text().strip()

    @output_dir.setter
    def output_dir(self, value: str) -> None:
        self._output.setText(value)

    @property
    def output_mode(self) -> str:
        return self._mode.currentData() if self._batch else "single"

    @output_mode.setter
    def output_mode(self, value: str) -> None:
        index = self._mode.findData(value)
        if index >= 0:
            self._mode.setCurrentIndex(index)

    @property
    def mode_selector_visible(self) -> bool:
        return not self._mode.isHidden()

    def select_format(self, format_id: str) -> bool:
        index = self._format.findData(format_id)
        if index < 0:
            return False
        self._format.setCurrentIndex(index)
        return True

    # -- Behavior --------------------------------------------------------

    def populate(self, last_format: str, last_quality: int, last_output_dir: str, batch_mode: str) -> None:
        """Restore persisted preferences; unknown values fall back to defaults."""
        if not self.select_format(last_format):
            self.select_format("JPG")
        if 1 <= last_quality <= 100:
            self.quality = last_quality
        self.output_dir = last_output_dir
        self.output_mode = batch_mode

    def build_options(self, files: list[str]) -> ConversionOptions:
        mode = self.output_mode
        common_root = None
        if mode == "mirror" and files:
            common_root = os.path.commonpath([os.path.dirname(f) for f in files])
        return ConversionOptions(
            target_format=self.selected_format_id,
            quality=self.quality,
            output_dir=self.output_dir,
            output_mode=mode,
            common_root=common_root,
        )

    # -- Internals -------------------------------------------------------

    def _update_quality_enabled(self) -> None:
        info = self._registry.get(self.selected_format_id)
        self._slider.setEnabled(bool(info and info.supports_quality))

    def _on_format_changed(self, _index: int) -> None:
        self._update_quality_enabled()
        self.changed.emit()

    def _on_quality_changed(self, value: int) -> None:
        self._value_label.setText(str(value))
        self.changed.emit()

    def _pick_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select output folder", self.output_dir)
        if folder:
            self.output_dir = folder
