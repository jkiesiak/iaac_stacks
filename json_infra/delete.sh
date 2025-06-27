#!/bin/bash
set -e

# Default values
PROFILE=""
REGION="eu-west-1"
STACK_NAME="MainStack-production"
BUCKET_NAME="upload-stacks-in-json"
PREFIX="nested"

# Usage info
usage() {
    echo "Usage: $0 -p <profile> [-r <region>] [-s <stack-name>] [-b <bucket-name>]"
    echo "  -p, --profile      AWS profile name (required)"
    echo "  -r, --region       AWS region (default: eu-west-1)"
    echo "  -s, --stack-name   CloudFormation stack name (default: MainStack-production)"
    echo "  -b, --bucket-name  S3 bucket name (default: upload-stacks-in-json)"
    echo "  -f, --force        Skip confirmation prompts"
    echo "  -h, --help         Show this help message"
    exit 1
}

# Parse arguments
FORCE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--profile) PROFILE="$2"; shift 2 ;;
        -r|--region) REGION="$2"; shift 2 ;;
        -s|--stack-name) STACK_NAME="$2"; shift 2 ;;
        -b|--bucket-name) BUCKET_NAME="$2"; shift 2 ;;
        -f|--force) FORCE=true; shift ;;
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

# Function to check if stack exists
check_stack_exists() {
    aws cloudformation describe-stacks --stack-name "$1" --profile "$PROFILE" --region "$REGION" >/dev/null 2>&1
}

# Function to check if bucket exists
check_bucket_exists() {
    aws s3api head-bucket --bucket "$1" --profile "$PROFILE" 2>/dev/null
}

# Function to wait for stack deletion
wait_for_stack_deletion() {
    local stack_name="$1"
    echo "⏳ Waiting for stack '$stack_name' to be deleted..."

    while check_stack_exists "$stack_name"; do
        local status=$(aws cloudformation describe-stacks --stack-name "$stack_name" --profile "$PROFILE" --region "$REGION" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "DELETE_COMPLETE")

        if [[ "$status" == "DELETE_FAILED" ]]; then
            echo "❌ Stack deletion failed. Check AWS Console for details."
            exit 1
        fi

        echo "   Stack status: $status"
        sleep 10
    done
    echo "✅ Stack '$stack_name' deleted successfully!"
}


echo ""
echo "🗑️  Starting resource deletion process..."
echo ""

# Delete CloudFormation Stack
if check_stack_exists "$STACK_NAME"; then
    echo "🔄 Deleting CloudFormation stack '$STACK_NAME'..."
    aws cloudformation delete-stack \
        --stack-name "$STACK_NAME" \
        --profile "$PROFILE" \
        --region "$REGION"

    wait_for_stack_deletion "$STACK_NAME"
else
    echo "ℹ️  Stack '$STACK_NAME' does not exist or is already deleted."
fi

# Delete S3 bucket contents
if check_bucket_exists "$BUCKET_NAME"; then
    echo "🔄 Deleting S3 bucket contents from s3://$BUCKET_NAME/$PREFIX/..."

    # List and delete objects with the prefix
    objects=$(aws s3api list-objects-v2 --bucket "$BUCKET_NAME" --prefix "$PREFIX/" --profile "$PROFILE" --query 'Contents[].Key' --output text 2>/dev/null || echo "")

    if [[ -n "$objects" && "$objects" != "None" ]]; then
        echo "   Found objects to delete:"
        echo "$objects" | tr '\t' '\n' | sed 's/^/     - /'

        aws s3 rm "s3://$BUCKET_NAME/$PREFIX/" --recursive --profile "$PROFILE"
        echo "✅ S3 bucket contents deleted successfully!"
    else
        echo "ℹ️  No objects found with prefix '$PREFIX/' in bucket '$BUCKET_NAME'."
    fi

    # Optional: Delete the entire bucket (uncomment if needed)
    # echo "🔄 Deleting S3 bucket '$BUCKET_NAME'..."
    # aws s3 rb "s3://$BUCKET_NAME" --profile "$PROFILE"
    # echo "✅ S3 bucket deleted successfully!"

else
    echo "ℹ️  Bucket '$BUCKET_NAME' does not exist or is not accessible."
fi

echo ""
echo "🎉 Resource deletion completed!"
echo ""
echo "Summary:"
echo "  ✅ CloudFormation stack '$STACK_NAME' - Deleted"
echo "  ✅ S3 objects in s3://$BUCKET_NAME/$PREFIX/ - Deleted"
echo "  ℹ️  S3 bucket '$BUCKET_NAME' - Preserved (objects only deleted)"
echo ""
echo "Note: If you want to delete the entire S3 bucket, uncomment the relevant lines in the script."