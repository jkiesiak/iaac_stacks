#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 -p <aws_profile> -e <environment_name>"
    echo "  -p, --profile       AWS profile to use"
    echo "  -e, --environment   Logical environment name (e.g. dev, prod)"
    exit 1
}

echo "---------- Step: Parse and validate input parameters ----------"

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
        -e|--environment)
            if [[ -n "$2" ]] && [[ ${2:0:1} != "-" ]]; then
                environment=$2
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

if [ -z "$aws_profile" ] || [ -z "$environment" ]; then
    echo "Error: Missing required parameters." >&2
    usage
fi

echo "---------- Step: Set AWS credentials for CDK ----------"
export AWS_PROFILE=$aws_profile
export AWS_DEFAULT_REGION="eu-west-1"

echo "Using AWS profile: $AWS_PROFILE"
echo "Target environment: $environment"

echo "---------- Step: Install dependencies if needed ----------"
pip3 install -r requirements.txt

echo "---------- Step: Bootstrap CDK environment if not already bootstrapped ----------"
cdk bootstrap --profile "$AWS_PROFILE"

echo "---------- Step: Synthesize the CDK app ----------"
cdk synth --context env="$environment" --profile "$AWS_PROFILE"

echo "---------- Step: Deploy the CDK stacks ----------"
cdk deploy --all --require-approval never --context env="$environment" --profile "$AWS_PROFILE"

echo "---------- Done. CDK stacks deployed. ----------"
