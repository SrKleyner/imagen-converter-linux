from PySide6.QtCore import QMimeData, QUrl

from src.gui.input_widget import InputWidget, expand_paths


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return str(path)


def test_expand_paths_recurses_and_filters_unsupported(tmp_path, registry):
    a = _touch(tmp_path / "a.png", )
    b = _touch(tmp_path / "sub" / "deep" / "b.JPG")
    _touch(tmp_path / "sub" / "notes.txt")
    result = expand_paths([str(tmp_path)], registry)
    assert sorted(result) == sorted([a, b])


def test_expand_paths_keeps_supported_files_and_dedupes(tmp_path, registry):
    a = _touch(tmp_path / "a.webp")
    txt = _touch(tmp_path / "a.txt")
    assert expand_paths([a, a, txt], registry) == [a]


def test_drop_of_file_urls_populates_batch_files(qapp, tmp_path, registry):
    a = _touch(tmp_path / "a.png")
    b = _touch(tmp_path / "dir" / "b.jpeg")
    widget = InputWidget(registry, batch=True)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(a), QUrl.fromLocalFile(str(tmp_path / "dir"))])
    assert widget.handle_mime(mime) is True
    assert sorted(widget.files) == sorted([a, b])


def test_single_mode_keeps_only_first_file(qapp, tmp_path, registry):
    a = _touch(tmp_path / "a.png")
    b = _touch(tmp_path / "b.png")
    widget = InputWidget(registry, batch=False)
    widget.add_paths([a, b])
    assert widget.files == [a]


def test_drop_without_urls_is_rejected(qapp, registry):
    widget = InputWidget(registry, batch=True)
    mime = QMimeData()
    mime.setText("hello")
    assert widget.handle_mime(mime) is False
    assert widget.files == []


def test_clear_empties_files_and_notifies(qapp, tmp_path, registry):
    seen = []
    widget = InputWidget(registry, batch=True, on_files_changed=seen.append)
    widget.add_paths([_touch(tmp_path / "a.png")])
    widget.clear()
    assert widget.files == []
    assert seen[-1] == []
