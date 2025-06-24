#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 -p <aws_profile> [-e <environment_name>]"
    echo "  -p, --profile       AWS profile to use (required)"
    echo "  -e, --environment   Logical environment name (e.g. dev, prod), optional (default: dev)"
    exit 1
}

# ---------- Step: Parse and validate input parameters ----------
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -p|--profile)
            if [[ -n "$2" && ${2:0:1} != "-" ]]; then
                aws_profile="$2"
                shift
            else
                echo "Error: Argument for $1 is missing" >&2
                usage
            fi
            ;;
        -e|--environment)
            if [[ -n "$2" && ${2:0:1} != "-" ]]; then
                environment="$2"
                shift
            else
                echo "Error: Argument for $1 is missing" >&2
                usage
            fi
            ;;
        *)
            echo "Error: Invalid option $1" >&2
            usage
            ;;
    esac
    shift
done

# Validate required parameter
if [ -z "$aws_profile" ]; then
    echo "Error: Missing required parameter --profile" >&2
    usage
fi

# Set default environment if not provided
environment="${environment:-dev}"

# ---------- Step: Set AWS credentials ----------
export AWS_PROFILE="$aws_profile"
export AWS_DEFAULT_REGION="eu-west-1"

echo "Using AWS profile: $AWS_PROFILE"
echo "Target environment: $environment"

# ---------- Step: Destroy CDK stacks ----------
cdk destroy --all --force --context env="$environment" --profile "$AWS_PROFILE"

echo "---------- Done. CDK stacks destroyed. ----------"
