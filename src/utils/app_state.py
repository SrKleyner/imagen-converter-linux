"""AppState — persistent user preferences as JSON.

Stored at ``~/.imagen-converter/config.json`` with atomic write and
corrupt-JSON recovery.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path


def _config_dir() -> Path:
    """Return the platform-appropriate config directory."""
    return Path.home() / ".imagen-converter"


def _config_path() -> Path:
    """Return the full path to ``config.json``."""
    return _config_dir() / "config.json"


@dataclass
class AppState:
    """User preferences persisted across application launches.

    Fields:
        theme: CustomTkinter appearance mode ("system", "dark", "light").
        last_output_dir: Most recently used output directory path.
        last_format: Canonical format id (e.g. "JPG", "WEBP").
        last_quality: Quality slider value 1–100.
        batch_mode: Output organization mode ("single" or "mirror").
    """

    theme: str = "system"
    last_output_dir: str = ""
    last_format: str = "JPG"
    last_quality: int = 85
    batch_mode: str = "single"

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        """Serialize to a plain dict suitable for JSON encoding."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AppState:
        """Construct an ``AppState`` from a dict, ignoring unknown keys.

        Missing keys use the dataclass defaults.
        """
        # Known field defaults
        defaults: dict[str, object] = {
            "theme": "system",
            "last_output_dir": "",
            "last_format": "JPG",
            "last_quality": 85,
            "batch_mode": "single",
        }
        merged = {**defaults, **{k: v for k, v in data.items() if k in defaults}}
        return cls(
            theme=str(merged["theme"]),
            last_output_dir=str(merged["last_output_dir"]),
            last_format=str(merged["last_format"]),
            last_quality=int(merged["last_quality"]),
            batch_mode=str(merged["batch_mode"]),
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_app_state() -> AppState:
    """Load ``AppState`` from ``~/.imagen-converter/config.json``.

    Returns the default ``AppState`` when:
    - The config directory does not exist.
    - The config file does not exist.
    - The config file contains invalid JSON (backed up to ``.corrupt``).
    """
    path = _config_path()

    if not path.exists():
        return AppState()

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return AppState()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Corrupt JSON → backup and return defaults
        _backup_corrupt(path, raw)
        return AppState()

    if not isinstance(data, dict):
        _backup_corrupt(path, raw)
        return AppState()

    return AppState.from_dict(data)


def save_app_state(state: AppState) -> None:
    """Persist *state* to ``~/.imagen-converter/config.json`` atomically.

    Writes to a temporary file first, then renames it over the target
    to avoid partial writes corrupting the config.
    """
    config_dir = _config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    target = _config_path()
    payload = json.dumps(state.to_dict(), indent=2)

    # Atomic write: tmp file + rename
    fd, tmp_path = tempfile.mkstemp(dir=str(config_dir), suffix=".tmp")
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)

    os.replace(tmp_path, str(target))


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _backup_corrupt(path: Path, raw: str) -> None:
    """Rename *path* to ``*.corrupt`` so the user can inspect it.

    On the next launch, a missing config file yields defaults.
    The *raw* content is preserved inside the renamed file.
    """
    corrupt_path = Path(str(path) + ".corrupt")
    try:
        # Remove a stale .corrupt if it exists, then move
        if corrupt_path.exists():
            corrupt_path.unlink()
        path.rename(corrupt_path)
    except OSError:
        pass  # best-effort; don't block launch on backup failure
