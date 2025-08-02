#!/bin/bash

set -e

PROFILE="${1:-user_infra}"
STACK_NAME="${2:-dev}"
PULUMI_CONFIG_PASSPHRASE=""
export PULUMI_CONFIG_PASSPHRASE=""
export AWS_PROFILE="$PROFILE"
export PULUMI_PYTHON_CMD=$(which python)
export AWS_REGION=eu-west-1
export AWS_DEFAULT_REGION=eu-west-1

# Check that S3 bucket exists (optional safety net)
aws s3 ls s3://upload-stacks-in-json --profile "$PROFILE" --region eu-west-1 > /dev/null 2>&1 || {
  echo "S3 bucket 'upload-stacks-in-json' does not exist or is not accessible."
  exit 1
}


# Log into self-managed S3 backend
pulumi login s3://upload-stacks-in-json

# Set AWS profile for both Pulumi and subprocesses

pulumi config set aws:profile "$PROFILE" --stack "$STACK_NAME"

# Select or create stack
pulumi stack select "$STACK_NAME" || pulumi stack init "$STACK_NAME"

# Deploy resources
pulumi up --yes --logtostderr --verbose=9

