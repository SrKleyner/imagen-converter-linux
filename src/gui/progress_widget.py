"""Progress widget — bar, status line, failure log and Cancel button (PF-*)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.batch.runner import ProgressEvent


class ProgressWidget(QWidget):
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._status = QLabel("Idle")
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Failed files appear here")
        self._cancel = QPushButton("Cancel")
        self._cancel.setEnabled(False)
        self._cancel.clicked.connect(self.cancel_requested.emit)

        top = QHBoxLayout()
        top.addWidget(self._bar, 1)
        top.addWidget(self._cancel)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self._status)
        layout.addWidget(self._log, 1)

    @property
    def percent(self) -> int:
        return self._bar.value()

    @property
    def status_text(self) -> str:
        return self._status.text()

    @property
    def log_text(self) -> str:
        return self._log.toPlainText()

    @property
    def cancel_enabled(self) -> bool:
        return self._cancel.isEnabled()

    def click_cancel(self) -> None:
        self._cancel.click()

    def set_running(self, running: bool) -> None:
        self._cancel.setEnabled(running)

    def reset(self) -> None:
        self._bar.setValue(0)
        self._status.setText("Idle")
        self._log.clear()

    def append_log(self, text: str) -> None:
        self._log.appendPlainText(text)

    def process_event(self, event: ProgressEvent) -> None:
        total = event.total
        if event.kind == "file_started":
            self._status.setText(f"{event.index} / {total}  {event.path or ''}")
            self._set_percent(event.index - 1, total)
        elif event.kind == "file_completed":
            self._set_percent(event.index, total)
        elif event.kind == "file_failed":
            self.append_log(f"Failed: {event.path} - {event.message or 'unknown error'}")
            self._set_percent(event.index, total)
        elif event.kind == "batch_completed":
            self._bar.setValue(100)
            self._status.setText(f"Done - {total} file(s) processed")
            self.set_running(False)
        elif event.kind == "batch_cancelled":
            self._status.setText(event.message or "Cancelled")
            self.set_running(False)

    def _set_percent(self, done: int, total: int) -> None:
        if total > 0:
            self._bar.setValue(int(done * 100 / total))
