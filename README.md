# Imagen Converter (Linux)

A desktop image format converter for Linux, built with PySide6 (Qt 6) and Pillow.
Convert single files or whole folders between AVIF, WebP, PNG and JPEG, with
drag-and-drop, quality control and a UI that follows your Plasma theme.

## Supported formats

| Format | Extension | Read | Write | Quality slider |
|--------|-----------|------|-------|----------------|
| AVIF | `.avif` | yes | yes | yes |
| WebP | `.webp` | yes | yes | yes |
| PNG | `.png` | yes | yes | no (lossless) |
| JPEG | `.jpg` `.jpeg` | yes | yes | yes |

AVIF is probed at startup; if the encoder is unavailable it is hidden from the
format dropdown and the rest keeps working.

## Why a separate Linux port

The Windows version uses customtkinter and tkinterdnd2. On Fedora, Tk 9 breaks
both (the tkdnd binaries do not load), and Tk has no native Wayland support, so
HiDPI looks blurry. This port uses Qt, which gives native Wayland/KDE behavior,
real drag-and-drop from Dolphin and automatic theme integration. The conversion
core is shared with the Windows build.

## Quick start

Requires Python 3.12+.

```bash
./run.sh
```

On first run it creates `.venv` and installs `requirements.txt`.

### Add it to the app menu

```bash
scripts/install-desktop.sh     # install launcher and icon in ~/.local/share
scripts/uninstall-desktop.sh   # remove them
```

## Usage

- **Single tab**: browse or drop one file, pick a format and quality, convert.
- **Batch tab**: browse or drop a folder (drag it straight from Dolphin), pick
  format and quality, then choose the output mode:
  - **Single folder**: all outputs go into one flat directory.
  - **Mirror structure**: subfolders are recreated in the output directory.
- **Quality**: slider 1-100 for lossy formats, disabled for PNG.
- **Cancel**: stops a running batch; files already converted are kept.
- Corrupt files are skipped in batch mode and reported in the log.

State (last format, quality, output folder) is stored in
`~/.imagen-converter/config.json`.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest
```

`QT_QPA_PLATFORM=offscreen` lets the GUI tests run without a display.

## Project structure

```
main.py              entry point
run.sh               launcher (creates .venv on first run)
assets/              app icon
scripts/             desktop entry install / uninstall
src/app.py           main window and run()
src/gui/             Qt widgets (input, options, progress)
src/core/            format handling and conversion (no Qt)
src/batch/           batch runner
src/utils/           paths and persisted state
tests/               unit, integration and GUI tests
```

## License

MIT — see [LICENSE](LICENSE).
