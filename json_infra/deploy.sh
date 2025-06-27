#!/bin/bash
set -e

# Default values
PROFILE=""
REGION="eu-west-1"
CAPABILITIES="CAPABILITY_IAM CAPABILITY_NAMED_IAM"

# Usage info
usage() {
    echo "Usage: $0 -p <profile> [-r <region>]"
    echo "  -p, --profile    AWS profile name (required)"
    echo "  -r, --region     AWS region (default: eu-west-1)"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--profile) PROFILE="$2"; shift 2 ;;
        -r|--region) REGION="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# Validate profile
if [[ -z "$PROFILE" ]]; then
    echo "❌ Error: AWS profile is required."
    usage
fi

if ! aws configure list-profiles | grep -q "^$PROFILE$"; then
    echo "❌ AWS profile '$PROFILE' not found!"
    aws configure list-profiles
    exit 1
fi

# Test access
echo "🔐 Validating AWS profile '$PROFILE'..."
aws sts get-caller-identity --profile "$PROFILE" >/dev/null || {
    echo "❌ Cannot access AWS with profile '$PROFILE'."
    exit 1
}
echo "✅ Profile valid. Region: $REGION"
echo ""

BUCKET_NAME="upload-stacks-in-json"
PREFIX="nested"

for file in MainStackproduction*Stackproduction*.template.json; do
  aws s3 cp "$file" "s3://$BUCKET_NAME/$PREFIX/$file"  --profile "$PROFILE"
done


TEMPLATE="MainStack-production.template.json"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "❌ Template file $TEMPLATE not found!"
  exit 1
fi

echo "🚀 Deploying MainStack-production..."
aws cloudformation deploy \
  --template-file "$TEMPLATE" \
  --stack-name MainStack-production \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --profile "$PROFILE" \
  --region "$REGION"

echo "✅ Deployment complete!"