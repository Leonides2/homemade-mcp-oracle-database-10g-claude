#!/usr/bin/env bash
# Instalador de un solo paso para Linux/macOS. Ver scripts/install.py para el detalle.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || PYTHON_BIN=python

exec "$PYTHON_BIN" scripts/install.py "$@"
