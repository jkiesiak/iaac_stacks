#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 -p <aws_profile> -w <workspace_name>"
    echo "  -p, --profile     AWS profile to use"
    echo "  -w, --workspace   Workspace name"
    exit 1
}

echo "---------- Operational step: Provide parameters to start infrastructure -------------------"

# Parse command-line options
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -p|--profile)
            if [[ -n "$2" ]] && [[ ${2:0:1} != "-" ]]; then
                aws_profile=$2
                shift
            else
                echo "Error: Argument for $1 is missing" >&2
                usage
            fi
            ;;
        -w|--workspace)
            if [[ -n "$2" ]] && [[ ${2:0:1} != "-" ]]; then
                workspace_name=$2
                shift
            else
                echo "Error: Argument for $1 is missing" >&2
                usage
            fi
            ;;
        *)  # unknown option/position
            echo "Error: Invalid option $1" >&2
            usage
            ;;
    esac
    shift
done

# Check if the required options are provided
if [ -z "$aws_profile" ] || [ -z "$workspace_name" ]; then
    echo "Error: Missing required options" >&2
    usage
fi

echo "---------- Operational step: export AWS_PROFILE to the environment ---------- "
export AWS_PROFILE=$aws_profile
export AWS_DEFAULT_REGION=eu-west-1

# Echo the provided inputs (or insert your script's operations here)
echo "Using AWS profile: $aws_profile"
echo "Workspace name: $workspace_name"

echo "---------- Operational step: verify AWS_PROFILE in the environment ---------- "
if [ -z "$aws_profile" ]; then
    echo "Error: AWS_PROFILE is not set. Please export the desired profile."
    exit 1
fi

terraform -chdir=./terraform init

echo "---------- Operational step: setup resources with provided workspace ---------- "
terraform -chdir=./terraform workspace new $workspace_name
terraform -chdir=./terraform workspace select $workspace_name

echo "---------- Operational step: clean-up of the code ---------- "
terraform -chdir=./terraform fmt

echo "---------- Operational step: start all resources ---------- "
terraform -chdir=./terraform apply -auto-approve -var is_development=true -lock=false
