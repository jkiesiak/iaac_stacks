#!/bin/bash

set -euxo pipefail
HERE=$(pwd)
PROJECT_ROOT="$HERE"
source "$PROJECT_ROOT/ci/config.env"

docker tag $REPOSITORY:$TAG $REPOSITORY:latest
docker tag $REPOSITORY:$TAG $AWS_ECR_REGISTRY/$REPOSITORY:$TAG
