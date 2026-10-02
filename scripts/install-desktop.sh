#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
ICON_DIR="$DATA/icons/hicolor/scalable/apps"
APP_DIR="$DATA/applications"

mkdir -p "$ICON_DIR" "$APP_DIR"
install -m 644 "$ROOT/assets/imagen-converter.svg" "$ICON_DIR/imagen-converter.svg"

cat > "$APP_DIR/imagen-converter.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Imagen Converter
Comment=Convert images between AVIF, WebP, PNG and JPEG
Exec="$ROOT/run.sh"
Icon=imagen-converter
Terminal=false
Categories=Graphics;Utility;
StartupWMClass=imagen-converter
Keywords=image;convert;webp;avif;png;jpg;
EOF

update-desktop-database "$APP_DIR" 2>/dev/null || true
gtk-update-icon-cache -q -t "$DATA/icons/hicolor" 2>/dev/null || true
echo "Installed launcher: $APP_DIR/imagen-converter.desktop"
