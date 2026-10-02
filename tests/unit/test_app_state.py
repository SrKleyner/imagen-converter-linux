"""Tests for src.utils.app_state — AppState persistence and recovery."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

import src.utils.app_state as app_state_mod
from src.utils.app_state import AppState, load_app_state, save_app_state


def _config_dir():
    return app_state_mod._config_dir()


def _config_path():
    return app_state_mod._config_path()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_config_dir(monkeypatch: pytest.MonkeyPatch) -> str:
    """Redirect .imagen-converter config to a temp directory."""
    with tempfile.TemporaryDirectory() as d:
        config_home = Path(d) / ".imagen-converter"
        monkeypatch.setattr(
            app_state_mod, "_config_dir", lambda: config_home
        )
        monkeypatch.setattr(
            app_state_mod, "_config_path", lambda: config_home / "config.json"
        )
        yield d


# ---------------------------------------------------------------------------
# AppState defaults
# ---------------------------------------------------------------------------


class TestAppStateDefaults:
    """Verify AppState field defaults."""

    def test_default_theme(self) -> None:
        state = AppState()
        assert state.theme == "system"

    def test_default_last_output_dir(self) -> None:
        state = AppState()
        assert state.last_output_dir == ""

    def test_default_last_format(self) -> None:
        state = AppState()
        assert state.last_format == "JPG"

    def test_default_last_quality(self) -> None:
        state = AppState()
        assert state.last_quality == 85

    def test_default_batch_mode(self) -> None:
        state = AppState()
        assert state.batch_mode == "single"


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    """AppState ↔ dict ↔ JSON round-trip."""

    def test_to_dict_round_trip(self) -> None:
        original = AppState(
            theme="dark",
            last_output_dir="/home/user/output",
            last_format="WEBP",
            last_quality=90,
            batch_mode="mirror",
        )
        data = original.to_dict()
        restored = AppState.from_dict(data)
        assert restored.theme == "dark"
        assert restored.last_output_dir == "/home/user/output"
        assert restored.last_format == "WEBP"
        assert restored.last_quality == 90
        assert restored.batch_mode == "mirror"

    def test_from_dict_with_extra_keys(self) -> None:
        """Unknown keys are silently ignored."""
        data = {
            "theme": "light",
            "last_output_dir": "/tmp",
            "last_format": "PNG",
            "last_quality": 50,
            "batch_mode": "single",
            "extra_field": "should be ignored",
        }
        state = AppState.from_dict(data)
        assert state.theme == "light"
        # extra_field should not appear (not a field on AppState)
        assert not hasattr(state, "extra_field")

    def test_from_dict_with_missing_keys(self) -> None:
        """Missing keys fall back to defaults."""
        data: dict[str, object] = {"theme": "dark"}
        state = AppState.from_dict(data)
        assert state.theme == "dark"
        assert state.last_output_dir == ""
        assert state.last_format == "JPG"
        assert state.last_quality == 85
        assert state.batch_mode == "single"

    def test_from_dict_empty(self) -> None:
        """Empty dict yields all defaults."""
        state = AppState.from_dict({})
        assert state.theme == "system"
        assert state.last_quality == 85


# ---------------------------------------------------------------------------
# JSON persistence — save and load
# ---------------------------------------------------------------------------


class TestPersistence:
    """Save → load round-trip via the filesystem."""

    def test_save_and_load_round_trip(self, temp_config_dir: str) -> None:
        state = AppState(
            theme="light",
            last_output_dir="/data/out",
            last_format="AVIF",
            last_quality=75,
            batch_mode="mirror",
        )
        save_app_state(state)
        loaded = load_app_state()
        assert loaded.theme == "light"
        assert loaded.last_output_dir == "/data/out"
        assert loaded.last_format == "AVIF"
        assert loaded.last_quality == 75
        assert loaded.batch_mode == "mirror"

    def test_load_defaults_when_missing(self, temp_config_dir: str) -> None:
        """When config file is missing, return defaults."""
        # Ensure no config file exists
        loaded = load_app_state()
        assert loaded.theme == "system"
        assert loaded.last_format == "JPG"
        assert loaded.last_quality == 85

    def test_config_dir_created_on_save(self, temp_config_dir: str) -> None:
        """Saving creates the .imagen-converter directory."""
        state = AppState()
        save_app_state(state)
        assert _config_dir().exists()
        assert _config_dir().is_dir()

    def test_config_file_is_valid_json(self, temp_config_dir: str) -> None:
        state = AppState(theme="dark", last_quality=42)
        save_app_state(state)
        path = _config_path()
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        assert parsed["theme"] == "dark"
        assert parsed["last_quality"] == 42


# ---------------------------------------------------------------------------
# Corrupt JSON recovery
# ---------------------------------------------------------------------------


class TestCorruptRecovery:
    """When config.json is corrupt, load returns defaults and creates backup."""

    def test_malformed_json_returns_defaults(self, temp_config_dir: str) -> None:
        cd = _config_dir()
        cd.mkdir(parents=True, exist_ok=True)
        _config_path().write_text("this is not json {{{broken", encoding="utf-8")

        state = load_app_state()
        # Should return defaults, not crash
        assert state.theme == "system"
        assert state.last_quality == 85

    def test_malformed_json_backs_up(self, temp_config_dir: str) -> None:
        cd = _config_dir()
        cd.mkdir(parents=True, exist_ok=True)
        corrupt_content = "not valid json at all"
        _config_path().write_text(corrupt_content, encoding="utf-8")

        load_app_state()

        # Original should be renamed to .corrupt
        corrupt_path = Path(str(_config_path()) + ".corrupt")
        assert corrupt_path.exists(), f"Expected .corrupt at {corrupt_path}"
        assert corrupt_path.read_text(encoding="utf-8") == corrupt_content

        # Original config.json should be gone (moved to .corrupt)
        assert not _config_path().exists()

    def test_empty_json_returns_defaults(self, temp_config_dir: str) -> None:
        cd = _config_dir()
        cd.mkdir(parents=True, exist_ok=True)
        _config_path().write_text("", encoding="utf-8")

        state = load_app_state()
        assert state.theme == "system"
        assert state.last_quality == 85

    def test_json_array_instead_of_object(self, temp_config_dir: str) -> None:
        cd = _config_dir()
        cd.mkdir(parents=True, exist_ok=True)
        _config_path().write_text("[1, 2, 3]", encoding="utf-8")

        state = load_app_state()
        assert state.theme == "system"


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    """Save writes to a tmp file first, then renames."""

    def test_no_tmp_left_behind(self, temp_config_dir: str) -> None:
        state = AppState()
        save_app_state(state)

        # No .tmp files should be left in the config dir
        tmp_files = list(_config_dir().glob("*.tmp"))
        assert len(tmp_files) == 0, f"Temporary files left: {tmp_files}"

    def test_overwrite_updates_file(self, temp_config_dir: str) -> None:
        state1 = AppState(theme="dark")
        save_app_state(state1)

        state2 = AppState(theme="light")
        save_app_state(state2)

        loaded = load_app_state()
        assert loaded.theme == "light"
