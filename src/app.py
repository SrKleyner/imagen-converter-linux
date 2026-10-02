"""Main window — tabs, AppState, queue drain loop and BatchRunner wiring.

GS-1: tabs for Single / Batch. GS-4: UI stays responsive; the worker thread
posts to a queue that a QTimer drains every 100 ms. The theme follows the
desktop palette (KDE Plasma); the persisted ``theme`` field is left untouched.
"""

from __future__ import annotations

import queue
import sys
import threading

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.batch.runner import BatchRunner, ProgressEvent
from src.core.converter import probe_avif
from src.core.formats import FormatRegistry
from src.gui.input_widget import InputWidget
from src.gui.options_widget import OptionsWidget
from src.gui.progress_widget import ProgressWidget
from src.utils.app_state import AppState, load_app_state, save_app_state

DRAIN_INTERVAL_MS = 100
APP_TITLE = "Imagen Converter"
DESKTOP_FILE_NAME = "imagen-converter"


class _Tab(QWidget):
    """One conversion tab: input, options, progress and a Convert button."""

    def __init__(self, registry: FormatRegistry, batch: bool) -> None:
        super().__init__()
        self.input = InputWidget(registry, batch=batch)
        self.options = OptionsWidget(registry, batch=batch)
        self.progress = ProgressWidget()
        self.button = QPushButton("Convert batch" if batch else "Convert")
        layout = QVBoxLayout(self)
        layout.addWidget(self.input)
        layout.addWidget(self.options)
        layout.addWidget(self.button)
        layout.addWidget(self.progress, 1)


class ImagenConverterApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(820, 700)

        self._registry = FormatRegistry(avif_available=probe_avif())
        self._state: AppState = load_app_state()
        self.progress_queue: queue.Queue[ProgressEvent] = queue.Queue()
        self.runner: BatchRunner | None = None
        self.worker_thread: threading.Thread | None = None
        self._active: _Tab | None = None

        self._single = _Tab(self._registry, batch=False)
        self._batch = _Tab(self._registry, batch=True)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._single, "Single")
        self.tabs.addTab(self._batch, "Batch")
        self.setCentralWidget(self.tabs)

        for tab, is_batch in ((self._single, False), (self._batch, True)):
            tab.button.clicked.connect(lambda _c=False, b=is_batch: self.start_conversion(b))
            tab.progress.cancel_requested.connect(self.cancel)
            tab.options.populate(
                self._state.last_format,
                self._state.last_quality,
                self._state.last_output_dir,
                self._state.batch_mode,
            )

        self._timer = QTimer(self)
        self._timer.setInterval(DRAIN_INTERVAL_MS)
        self._timer.timeout.connect(self.drain_queue)
        self._timer.start()

    # -- Test-friendly accessors ----------------------------------------

    @property
    def single_input(self) -> InputWidget:
        return self._single.input

    @property
    def single_options(self) -> OptionsWidget:
        return self._single.options

    @property
    def single_progress(self) -> ProgressWidget:
        return self._single.progress

    @property
    def batch_options(self) -> OptionsWidget:
        return self._batch.options

    @property
    def batch_progress(self) -> ProgressWidget:
        return self._batch.progress

    @property
    def single_convert_enabled(self) -> bool:
        return self._single.button.isEnabled()

    @property
    def batch_convert_enabled(self) -> bool:
        return self._batch.button.isEnabled()

    # -- Conversion orchestration ---------------------------------------

    def begin_active(self, batch: bool) -> None:
        """Mark a tab as running so the drain loop targets it even after tab switches."""
        tab = self._batch if batch else self._single
        tab.progress.reset()
        tab.progress.set_running(True)
        tab.button.setEnabled(False)
        self._active = tab

    def start_conversion(self, batch: bool) -> None:
        tab = self._batch if batch else self._single
        files = tab.input.files
        if not files:
            tab.progress.append_log("No files selected.")
            return
        if not tab.options.output_dir:
            tab.progress.append_log("Please select an output folder.")
            return
        try:
            opts = tab.options.build_options(files)
        except ValueError as exc:
            tab.progress.append_log(str(exc))
            return

        self._remember(tab.options)
        self.begin_active(batch)
        self.runner = BatchRunner(files, opts)
        self.worker_thread = threading.Thread(
            target=self.runner.start, args=(self.progress_queue,), daemon=True
        )
        self.worker_thread.start()

    def cancel(self) -> None:
        if self.runner:
            self.runner.cancel()

    def drain_queue(self) -> None:
        """Apply all pending progress events to the active tab."""
        while True:
            try:
                event = self.progress_queue.get_nowait()
            except queue.Empty:
                return
            tab = self._active
            if tab is None:
                continue
            tab.progress.process_event(event)
            if event.kind in ("batch_completed", "batch_cancelled"):
                tab.button.setEnabled(True)
                self._active = None

    # -- Persistence ----------------------------------------------------

    def _remember(self, options: OptionsWidget) -> None:
        self._state.last_format = options.selected_format_id
        self._state.last_quality = options.quality
        self._state.last_output_dir = options.output_dir
        self._state.batch_mode = self._batch.options.output_mode

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._remember(self._batch.options)
        save_app_state(self._state)
        super().closeEvent(event)


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setDesktopFileName(DESKTOP_FILE_NAME)
    window = ImagenConverterApp()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
