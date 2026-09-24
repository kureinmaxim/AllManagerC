#!/bin/bash
# Double-click in Finder to build and reveal the installer.
cd "$(dirname "$0")" || exit 1
if ! bash build_macos.sh --open; then
    printf '\nBuild failed. Press Enter to close this window.'
    read -r
    exit 1
fi
