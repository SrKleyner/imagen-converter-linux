# Feature: linux-qt-gui

## Objective
Port Imagen Converter (Windows, CustomTkinter) to Linux (Fedora 44, KDE Plasma, Wayland) with a PySide6 GUI.

## Problem / Why
The original GUI depends on customtkinter + tkinterdnd2, built for Tk 8.6. Fedora 44 ships Tk 9.0, the
tkdnd binaries do not load, Tk has no native Wayland support (blurry on HiDPI), and system Python has no pip.

## Scope
- Reuse `src/core`, `src/batch`, `src/utils` and their tests unchanged (source: ../Imagen-converter).
- New Qt GUI with feature parity: Single/Batch tabs, browse + drag-and-drop, format dropdown
  (AVIF hidden when unavailable), quality slider (disabled for PNG), single/mirror output modes,
  output folder picker, progress bar + log, cancel, persisted state, theme follows Plasma.
- Linux packaging: run script, `.desktop` launcher, README.

## Constraints
- Dependencies only inside `.venv` (PySide6-Essentials, Pillow, pytest). No sudo.
- GUI must never import PIL (keep the core boundary).
- TDD: strict, runner `.venv/bin/python -m pytest` (source: user global CLAUDE.md "Strict TDD Mode: enabled").
  GUI tests run with `QT_QPA_PLATFORM=offscreen`.

## Delivery
Strategy: ask-on-risk. Forecast ~700 authored lines (mostly GUI + tests).

## Tasks
- [x] T1 Baseline: copy core/batch/utils + tests, venv, 96 tests green on Linux. Route: inline (mechanical copy).
- [ ] T2 Qt GUI (app window, input, options, progress widgets) with offscreen tests. Route: delegated writer (2+ non-trivial files).
- [ ] T3 Linux packaging: `main.py`, `run.sh`, `.desktop` install script, pyproject/requirements, README. Route: delegated writer.

## Acceptance criteria
- `pytest` green; app launches on Wayland; drag-and-drop from Dolphin works; conversion of single file and folder works.

## Progress / Evidence
- T1: `pytest -q` → 96 passed; `probe_avif()` → True (Pillow 12.3.0, PySide6 6.11.2).

## Next step
T2.
