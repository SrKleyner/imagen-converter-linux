#!/usr/bin/env bash
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA/applications"

rm -f "$DATA/icons/hicolor/scalable/apps/imagen-converter.svg"
rm -f "$APP_DIR/imagen-converter.desktop"

update-desktop-database "$APP_DIR" 2>/dev/null || true
echo "Removed Imagen Converter launcher."
