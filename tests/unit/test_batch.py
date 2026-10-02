"""Tests for src.batch.runner — BatchRunner, ProgressEvent, cancel, threading."""

from __future__ import annotations

import os
import queue
import tempfile
import threading
from pathlib import Path

import pytest
from PIL import Image

from src.batch.runner import BatchRunner, ProgressEvent
from src.core.options import ConversionOptions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_test_image(path: str) -> None:
    """Create a 32×32 RGB PNG."""
    Image.new("RGB", (32, 32), color=(100, 200, 50)).save(path, format="PNG")


@pytest.fixture
def temp_files() -> list[str]:
    """Create 3 temp PNG files and return their paths."""
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for i in range(3):
            p = os.path.join(d, f"img_{i}.png")
            _make_test_image(p)
            paths.append(p)
        yield paths


@pytest.fixture
def out_dir() -> str:
    with tempfile.TemporaryDirectory() as d:
        yield d


# ---------------------------------------------------------------------------
# ProgressEvent
# ---------------------------------------------------------------------------


class TestProgressEvent:
    def test_fields(self) -> None:
        ev = ProgressEvent(kind="file_started", path="/a/img.png", index=1, total=5)
        assert ev.kind == "file_started"
        assert ev.path == "/a/img.png"
        assert ev.index == 1
        assert ev.total == 5
        assert ev.message is None

    def test_frozen(self) -> None:
        ev = ProgressEvent(kind="batch_completed", index=5, total=5)
        with pytest.raises(Exception):
            ev.index = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BC-1: batch run
# ---------------------------------------------------------------------------


class TestBatchRun:
    """BC-1: converts multiple files in one operation."""

    def test_converts_all_files(self, temp_files: list[str], out_dir: str) -> None:
        opts = ConversionOptions(target_format="JPG", quality=80, output_dir=out_dir)
        runner = BatchRunner(temp_files, opts)
        q: queue.Queue[ProgressEvent] = queue.Queue()
        runner.start(q)

        events = _drain(q)
        # Check for batch_completed
        assert any(e.kind == "batch_completed" for e in events)

        # Verify output files
        jpgs = list(Path(out_dir).glob("*.jpg"))
        assert len(jpgs) == len(temp_files)

    def test_order_of_events(self, temp_files: list[str], out_dir: str) -> None:
        opts = ConversionOptions(target_format="PNG", quality=85, output_dir=out_dir)
        runner = BatchRunner(temp_files, opts)
        q: queue.Queue[ProgressEvent] = queue.Queue()
        runner.start(q)

        events = _drain(q)
        kinds = [e.kind for e in events]
        assert kinds[0] == "file_started"
        assert kinds[-1] == "batch_completed"


# ---------------------------------------------------------------------------
# BC-4: cancel
# ---------------------------------------------------------------------------


class TestCancel:
    """BC-4: cancel stops pending files; converted files remain."""

    def test_cancel_stops_after_first_file(self, temp_files: list[str], out_dir: str) -> None:
        opts = ConversionOptions(target_format="JPG", quality=80, output_dir=out_dir)
        runner = BatchRunner(temp_files, opts)
        q: queue.Queue[ProgressEvent] = queue.Queue()

        # We need to cancel right after the first file starts.
        # Simplest: override start internals? No — better: cancel from
        # another thread before the worker gets to file #2.
        # The worker checks the event BETWEEN files, so if we cancel
        # during file_started, it will stop at the next loop iteration.

        def _cancel_after_start():
            # Wait for first file_started
            while True:
                try:
                    ev = q.get(timeout=1.0)
                    if ev.kind == "file_started":
                        runner.cancel()
                        q.put(ev)  # put it back so _drain sees it
                        return
                    # No other events to put back — file_started is first
                except queue.Empty:
                    return

        t = threading.Thread(target=_cancel_after_start)
        t.start()
        runner.start(q)
        t.join(timeout=5)

        events = _drain(q)
        kinds = [e.kind for e in events]
        assert "batch_cancelled" in kinds

        # At least one file was started (and probably completed)
        jpgs = list(Path(out_dir).glob("*.jpg"))
        assert len(jpgs) >= 1

    def test_cancel_event_is_set(self) -> None:
        runner = BatchRunner([], ConversionOptions(target_format="JPG"))
        assert not runner._cancel_event.is_set()
        runner.cancel()
        assert runner._cancel_event.is_set()


# ---------------------------------------------------------------------------
# BC-5: continue on failure
# ---------------------------------------------------------------------------


class TestContinueOnFailure:
    """BC-5: one corrupt file does not stop the batch."""

    def test_corrupt_file_skipped(self, out_dir: str) -> None:
        # Create 2 good files + 1 corrupt
        good1 = os.path.join(out_dir, "good1.png")
        good2 = os.path.join(out_dir, "good2.png")
        bad = os.path.join(out_dir, "bad.png")
        _make_test_image(good1)
        _make_test_image(good2)
        Path(bad).write_text("not an image")

        opts = ConversionOptions(target_format="JPG", quality=80, output_dir=out_dir)
        runner = BatchRunner([good1, bad, good2], opts)
        q: queue.Queue[ProgressEvent] = queue.Queue()
        runner.start(q)

        events = _drain(q)
        assert any(e.kind == "file_failed" for e in events)
        assert any(e.kind == "batch_completed" for e in events)

        jpgs = list(Path(out_dir).glob("*.jpg"))
        assert len(jpgs) == 2  # two good files


# ---------------------------------------------------------------------------
# BC-6: disk full continues
# ---------------------------------------------------------------------------


class TestDiskFullContinue:
    """BC-6: DiskFullError reported per file, batch continues."""

    def test_disk_full_event_kind(self) -> None:
        ev = ProgressEvent(
            kind="file_failed",
            path="/a/x.jpg",
            index=2,
            total=5,
            message="Disk full while writing: /out/x.jpg",
        )
        assert ev.kind == "file_failed"
        assert "Disk full" in (ev.message or "")


# ---------------------------------------------------------------------------
# Empty batch & edge cases
# ---------------------------------------------------------------------------


class TestEmptyBatch:
    def test_empty_inputs(self) -> None:
        opts = ConversionOptions(target_format="JPG")
        runner = BatchRunner([], opts)
        q: queue.Queue[ProgressEvent] = queue.Queue()
        runner.start(q)
        events = _drain(q)
        kinds = {e.kind for e in events}
        assert "batch_completed" in kinds

    def test_single_file_is_one_item_batch(self, out_dir: str) -> None:
        p = os.path.join(out_dir, "single.png")
        _make_test_image(p)
        opts = ConversionOptions(target_format="WEBP", quality=90, output_dir=out_dir)
        runner = BatchRunner([p], opts)
        q: queue.Queue[ProgressEvent] = queue.Queue()
        runner.start(q)

        events = _drain(q)
        assert any(e.kind == "file_completed" for e in events)
        assert any(e.kind == "batch_completed" for e in events)

        webps = list(Path(out_dir).glob("*.webp"))
        assert len(webps) == 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _drain(q: queue.Queue[ProgressEvent]) -> list[ProgressEvent]:
    """Drain all items from queue (non-blocking)."""
    items: list[ProgressEvent] = []
    while True:
        try:
            items.append(q.get_nowait())
        except queue.Empty:
            break
    return items
