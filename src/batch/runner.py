"""Batch runner — threaded converter with progress queue and cancel support.

D2: single-file conversion reuses the same BatchRunner (1-item batch).
D3: progress flows worker → ``queue.Queue`` → GUI via ``root.after``.
D4: cancel uses ``threading.Event`` checked between files (BC-4).

BC-1: converts multiple files in one operation.
BC-4: cancel stops pending files; already-converted outputs are kept.
BC-5: continues on single-file failure.
BC-6: disk-full fails per file, batch continues.
PF-1..PF-4: progress events carry index/total/path for GUI rendering.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass

from src.core.converter import (
    ConversionError,
    convert_one,
)
from src.core.options import ConversionOptions
from src.utils.paths import resolve_output_path


@dataclass(frozen=True)
class ProgressEvent:
    """Typed message posted to the progress queue.

    Kinds:
        file_started, file_completed, file_failed,
        batch_completed, batch_cancelled.
    """

    kind: str  # file_started | file_completed | file_failed | batch_completed | batch_cancelled
    path: str | None = None  # input path for the file being processed
    index: int = 0  # 1-based index of current file
    total: int = 0  # total files in batch
    message: str | None = None  # error detail for file_failed / batch_cancelled


class BatchRunner:
    """Converts a list of input files in a background thread.

    Usage ::

        runner = BatchRunner(paths, options)
        runner.start(progress_queue)          # blocks until work finishes
        runner.cancel()                       # signal from main thread

    The worker thread posts ``ProgressEvent`` objects to *progress_queue*
    before/after each file and on terminal events.
    """

    def __init__(self, inputs: list[str], opts: ConversionOptions) -> None:
        self._inputs = list(inputs)
        self._opts = opts
        self._cancel_event = threading.Event()
        self._running = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, progress_queue: queue.Queue[ProgressEvent]) -> None:
        """Run the batch conversion **synchronously** (call from worker thread).

        Posts progress events to *progress_queue*.
        """
        with self._lock:
            if self._running:
                return
            self._running = True

        total = len(self._inputs)
        target_ext = self._get_target_ext()
        try:
            for idx, input_path in enumerate(self._inputs, start=1):
                if self._cancel_event.is_set():
                    progress_queue.put(
                        ProgressEvent(
                            kind="batch_cancelled",
                            index=idx,
                            total=total,
                            message=f"Cancelled — {total - idx + 1} file(s) skipped",
                        )
                    )
                    return

                progress_queue.put(
                    ProgressEvent(
                        kind="file_started",
                        path=input_path,
                        index=idx,
                        total=total,
                    )
                )

                try:
                    out_path = resolve_output_path(
                        input_path,
                        target_ext,
                        self._opts.output_dir,
                        output_mode=self._opts.output_mode,
                        common_root=self._opts.common_root,
                    )
                    convert_one(input_path, out_path, self._opts)
                    progress_queue.put(
                        ProgressEvent(
                            kind="file_completed",
                            path=input_path,
                            index=idx,
                            total=total,
                        )
                    )
                except ConversionError as exc:
                    progress_queue.put(
                        ProgressEvent(
                            kind="file_failed",
                            path=input_path,
                            index=idx,
                            total=total,
                            message=str(exc),
                        )
                    )
                    # BC-5 / BC-6: continue to next file
                    continue
        finally:
            with self._lock:
                self._running = False
            if not self._cancel_event.is_set():
                progress_queue.put(
                    ProgressEvent(
                        kind="batch_completed",
                        index=total,
                        total=total,
                    )
                )

    def cancel(self) -> None:
        """Signal the worker to stop before the next file (BC-4)."""
        self._cancel_event.set()

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_target_ext(self) -> str:
        """Derive target extension from options."""
        from src.core.formats import FormatRegistry

        # Build a small registry just for extension lookup
        registry = FormatRegistry(avif_available=True)
        info = registry.get(self._opts.target_format)
        if info:
            return info.ext
        # Fallback: map common formats
        ext_map = {"JPG": ".jpg", "PNG": ".png", "WEBP": ".webp", "AVIF": ".avif"}
        return ext_map.get(self._opts.target_format.upper(), ".jpg")
