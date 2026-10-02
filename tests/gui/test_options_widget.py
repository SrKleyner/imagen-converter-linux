import os

from src.gui.options_widget import OptionsWidget


def test_png_disables_quality(qapp, registry):
    w = OptionsWidget(registry, batch=False)
    w.select_format("PNG")
    assert not w.quality_enabled
    w.select_format("JPG")
    assert w.quality_enabled


def test_avif_hidden_when_unavailable(qapp, no_avif_registry, registry):
    assert "AVIF" not in OptionsWidget(no_avif_registry, batch=False).format_ids
    assert "AVIF" in OptionsWidget(registry, batch=False).format_ids


def test_build_options_single_mode(qapp, registry):
    w = OptionsWidget(registry, batch=False)
    w.select_format("WEBP")
    w.quality = 70
    w.output_dir = "/out"
    opts = w.build_options(["/in/a.png"])
    assert (opts.target_format, opts.quality, opts.output_dir) == ("WEBP", 70, "/out")
    assert opts.output_mode == "single" and opts.common_root is None


def test_build_options_mirror_computes_common_root(qapp, registry):
    w = OptionsWidget(registry, batch=True)
    w.output_mode = "mirror"
    w.output_dir = "/out"
    opts = w.build_options(["/photos/a/x.png", "/photos/b/y.png"])
    assert opts.output_mode == "mirror"
    assert opts.common_root == os.path.commonpath(["/photos/a", "/photos/b"])


def test_mirror_common_root_of_single_file_is_its_directory(qapp, registry):
    w = OptionsWidget(registry, batch=True)
    w.output_mode = "mirror"
    opts = w.build_options(["/photos/a/x.png"])
    assert opts.common_root == "/photos/a"


def test_populate_from_state(qapp, registry):
    w = OptionsWidget(registry, batch=True)
    w.populate(last_format="PNG", last_quality=42, last_output_dir="/o", batch_mode="mirror")
    assert (w.selected_format_id, w.quality, w.output_dir, w.output_mode) == ("PNG", 42, "/o", "mirror")


def test_populate_unknown_format_falls_back(qapp, no_avif_registry):
    w = OptionsWidget(no_avif_registry, batch=False)
    w.populate(last_format="AVIF", last_quality=85, last_output_dir="", batch_mode="single")
    assert w.selected_format_id == "JPG"


def test_mode_selector_only_in_batch(qapp, registry):
    assert not OptionsWidget(registry, batch=False).mode_selector_visible
    assert OptionsWidget(registry, batch=True).mode_selector_visible
