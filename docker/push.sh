#!/bin/bash

set -euxo pipefail
HERE=$(pwd)
PROJECT_ROOT="$HERE"
source "$PROJECT_ROOT/ci/config.env"

docker push $AWS_ECR_REGISTRY/$REPOSITORY:$TAG
