#!/bin/bash
set -euxo pipefail

HERE=$(realpath "$(dirname "$0")")
PROJECT_ROOT="$HERE/.."

cd "$PROJECT_ROOT"

# Check if the first argument is --dev
if [[ "${1:-}" == "--dev" ]]; then
    poetry install --with dev
else
    poetry install
fi

