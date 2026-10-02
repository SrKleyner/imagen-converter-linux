import queue
import threading
from pathlib import Path

import pytest
from PIL import Image

import src.app as app_module
from src.batch.runner import ProgressEvent
from src.utils.app_state import AppState


@pytest.fixture
def saved(monkeypatch):
    store = {}
    monkeypatch.setattr(app_module, "load_app_state", lambda: AppState(last_format="PNG", last_quality=33, batch_mode="mirror"))
    monkeypatch.setattr(app_module, "save_app_state", lambda s: store.update(state=s))
    return store


@pytest.fixture
def window(qapp, saved):
    w = app_module.ImagenConverterApp()
    yield w
    w.close()


def test_state_restored_on_start(window):
    assert window.batch_options.selected_format_id == "PNG"
    assert window.batch_options.quality == 33
    assert window.batch_options.output_mode == "mirror"


def test_state_saved_on_close(qapp, saved):
    w = app_module.ImagenConverterApp()
    w.batch_options.select_format("WEBP")
    w.batch_options.quality = 61
    w.close()
    st = saved["state"]
    assert (st.last_format, st.last_quality) == ("WEBP", 61)


def test_convert_without_files_logs_and_stays_enabled(window):
    window.start_conversion(batch=False)
    assert "No files" in window.single_progress.log_text
    assert window.single_convert_enabled


def test_drain_updates_progress_and_reenables_button(window):
    window.begin_active(batch=True)
    assert not window.batch_convert_enabled
    q = window.progress_queue
    q.put(ProgressEvent("file_started", "/a.png", 1, 2))
    q.put(ProgressEvent("file_completed", "/a.png", 1, 2))
    window.drain_queue()
    assert window.batch_progress.percent == 50
    assert not window.batch_convert_enabled
    q.put(ProgressEvent("batch_completed", None, 2, 2))
    window.drain_queue()
    assert window.batch_progress.percent == 100
    assert window.batch_convert_enabled


def test_drain_targets_conversion_tab_after_switching(window):
    window.begin_active(batch=True)
    window.tabs.setCurrentIndex(0)
    window.progress_queue.put(ProgressEvent("file_completed", "/a.png", 1, 4))
    window.drain_queue()
    assert window.batch_progress.percent == 25
    assert window.single_progress.percent == 0


def test_real_conversion_end_to_end(window, tmp_path):
    src = tmp_path / "in.png"
    Image.new("RGB", (4, 4), "red").save(src)
    out = tmp_path / "out"
    out.mkdir()
    window.single_input.add_paths([str(src)])
    window.single_options.output_dir = str(out)
    window.single_options.select_format("JPG")
    window.start_conversion(batch=False)
    window.worker_thread.join(timeout=10)
    window.drain_queue()
    assert (out / "in.jpg").exists()
    assert window.single_convert_enabled


def test_cancel_calls_runner_cancel(window):
    class R:
        called = False
        def cancel(self):
            R.called = True
    window.runner = R()
    window.cancel()
    assert R.called
