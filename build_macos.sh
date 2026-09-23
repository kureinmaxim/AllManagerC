#!/bin/bash
# Build in a new output directory; use --stage app / dmg for separate steps.
set -euo pipefail
cd "$(dirname "$0")"
BUILD_PYTHON="${BUILD_PYTHON:-.venv/bin/python}"
exec "$BUILD_PYTHON" tools/build_macos.py "$@"
