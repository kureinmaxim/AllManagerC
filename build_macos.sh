#!/bin/bash
# Build for this Mac. Version and output paths are chosen automatically.
set -euo pipefail
cd "$(dirname "$0")"
BUILD_PYTHON="${BUILD_PYTHON:-.venv/bin/python}"
if [[ ! -x "$BUILD_PYTHON" ]]; then
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        exec python3 tools/build_macos.py "$@"
    fi
    printf '%s\n' 'Python environment not found. Run once:' \
        '  python3 -m venv .venv' \
        '  .venv/bin/python -m pip install -r requirements-build-macos.txt' >&2
    exit 1
fi
exec "$BUILD_PYTHON" tools/build_macos.py "$@"
