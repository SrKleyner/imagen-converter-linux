from src.batch.runner import ProgressEvent
from src.gui.progress_widget import ProgressWidget


def test_events_update_bar_and_status(qapp):
    w = ProgressWidget()
    w.set_running(True)
    w.process_event(ProgressEvent("file_started", "/a.png", 1, 4))
    assert w.percent == 0 and "1 / 4" in w.status_text
    w.process_event(ProgressEvent("file_completed", "/a.png", 1, 4))
    assert w.percent == 25


def test_failed_file_is_logged(qapp):
    w = ProgressWidget()
    w.process_event(ProgressEvent("file_failed", "/bad.png", 1, 1, "corrupt"))
    assert "/bad.png" in w.log_text and "corrupt" in w.log_text


def test_terminal_events_disable_cancel(qapp):
    w = ProgressWidget()
    w.set_running(True)
    assert w.cancel_enabled
    w.process_event(ProgressEvent("batch_completed", None, 2, 2))
    assert not w.cancel_enabled and w.percent == 100


def test_cancel_button_emits_signal(qapp):
    w = ProgressWidget()
    hits = []
    w.cancel_requested.connect(lambda: hits.append(1))
    w.set_running(True)
    w.click_cancel()
    assert hits == [1]


def test_cancelled_shows_message(qapp):
    w = ProgressWidget()
    w.process_event(ProgressEvent("batch_cancelled", None, 2, 5, "Cancelled — 4 file(s) skipped"))
    assert "Cancelled" in w.status_text
