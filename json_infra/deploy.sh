#!/bin/bash
set -e

# Default values
PROFILE=""
REGION="eu-west-1"
CAPABILITIES="CAPABILITY_IAM CAPABILITY_NAMED_IAM"

# Function to display usage
usage() {
    echo "Usage: $0 -p <profile> [-r <region>]"
    echo "  -p, --profile    AWS profile name (required)"
    echo "  -r, --region     AWS region (default: eu-west-1)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -p user13"
    echo "  $0 -p user13 -r us-east-1"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if profile is provided
if [[ -z "$PROFILE" ]]; then
    echo "Error: AWS profile is required!"
    echo ""
    usage
fi

# Verify profile exists
if ! aws configure list-profiles | grep -q "^$PROFILE$"; then
    echo "Error: AWS profile '$PROFILE' not found!"
    echo "Available profiles:"
    aws configure list-profiles
    exit 1
fi

# Test profile access
echo "Testing AWS profile '$PROFILE'..."
if ! aws sts get-caller-identity --profile "$PROFILE" >/dev/null 2>&1; then
    echo "Error: Cannot access AWS with profile '$PROFILE'. Please check your credentials."
    exit 1
fi

echo "✅ AWS Profile '$PROFILE' is valid"
echo "🌍 Deploying to region: $REGION"
echo "🚀 Starting deployment..."
echo ""

# Function to deploy stack
deploy_stack() {
    local template_file=$1
    local stack_name=$2
    local description=$3

    echo "📦 Deploying $description..."
    if aws cloudformation deploy \
        --template-file "$template_file" \
        --stack-name "$stack_name" \
        --capabilities $CAPABILITIES \
        --profile "$PROFILE" \
        --region "$REGION" \
        --no-fail-on-empty-changeset; then
        echo "✅ $description deployed successfully"
    else
        echo "❌ Failed to deploy $description"
        exit 1
    fi
    echo ""
}

# Check if template files exist
templates=(
    "VpcStack.template.json:vpc-stack:VPC Stack"
    "RDSStack.template.json:rds-stack:RDS Stack"
    "LambdaRdsStack.template.json:lambda-rds-stack:Lambda RDS Stack"
    "ApiGatewayStack.template.json:api-gateway-stack:API Gateway Stack"
)

echo "🔍 Checking template files..."
for template_info in "${templates[@]}"; do
    IFS=':' read -r template_file stack_name description <<< "$template_info"
    if [[ ! -f "$template_file" ]]; then
        echo "❌ Template file '$template_file' not found!"
        echo "Make sure you have run 'cdk synth' and copied the template files."
        exit 1
    fi
done
echo "✅ All template files found"
echo ""

# Deploy stacks in order
echo "🎯 Starting stack deployment..."
echo ""

# Deploy VPC first (no dependencies)
deploy_stack "VpcStack.template.json" "vpc-stack" "VPC Stack"

# Deploy RDS (depends on VPC)
deploy_stack "RDSStack.template.json" "rds-stack" "RDS Stack"

# Deploy Lambda (depends on VPC and RDS)
deploy_stack "LambdaRdsStack.template.json" "lambda-rds-stack" "Lambda RDS Stack"

# Deploy API Gateway last (depends on Lambda)
deploy_stack "ApiGatewayStack.template.json" "api-gateway-stack" "API Gateway Stack"

echo "🎉 All stacks deployed successfully!"
echo ""
echo "📊 Stack Summary:"
aws cloudformation list-stacks \
    --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'StackSummaries[?contains(StackName, `vpc-stack`) || contains(StackName, `rds-stack`) || contains(StackName, `lambda-rds-stack`) || contains(StackName, `api-gateway-stack`)].{StackName:StackName, Status:StackStatus, Created:CreationTime}' \
    --output table

echo ""
echo "🔗 To get stack outputs:"
echo "aws cloudformation describe-stacks --stack-name <stack-name> --profile $PROFILE --region $REGION --query 'Stacks[0].Outputs'"