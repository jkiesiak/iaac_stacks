#!/bin/bash

set -euxo pipefail
HERE=$(pwd)
PROJECT_ROOT="$HERE"
source "$PROJECT_ROOT/ci/config.env"

aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin $AWS_ECR_REGISTRY
