#!/bin/bash

set -euxo pipefail
HERE=$(pwd)
PROJECT_ROOT="$HERE"
source "$PROJECT_ROOT/ci/config.env"

DOCKER_BUILDKIT=1 docker build \
 -t "${REPOSITORY}:${TAG}" \
 -f "$HERE/ci/Dockerfile" \
 --progress plain \
 "$PROJECT_ROOT"
