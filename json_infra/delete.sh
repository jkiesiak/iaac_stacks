#!/bin/bash
set -e

# Default values
PROFILE=""
REGION="eu-west-1"

# Function to display usage
usage() {
    echo "Usage: $0 -p <profile> [-r <region>] [-f]"
    echo "  -p, --profile    AWS profile name (required)"
    echo "  -r, --region     AWS region (default: eu-west-1)"
    echo "  -f, --force      Skip confirmation prompt"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 -p user13"
    echo "  $0 -p user13 -r us-east-1"
    echo "  $0 -p user13 -f  # Skip confirmation"
    exit 1
}

# Parse command line arguments
FORCE=false
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
        -f|--force)
            FORCE=true
            shift
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
echo "🌍 Working with region: $REGION"
echo ""

# Define stacks in reverse order (opposite of deployment order)
stacks=(
    "api-gateway-stack:API Gateway Stack"
    "lambda-rds-stack:Lambda RDS Stack"
    "rds-stack:RDS Stack"
    "vpc-stack:VPC Stack"
)

# Function to check if stack exists
stack_exists() {
    local stack_name=$1
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --profile "$PROFILE" \
        --region "$REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text >/dev/null 2>&1
}

# Function to delete stack
delete_stack() {
    local stack_name=$1
    local description=$2

    echo "🗑️  Deleting $description..."

    # Check if stack exists
    if stack_exists "$stack_name"; then
        # Get current stack status
        local stack_status
        stack_status=$(aws cloudformation describe-stacks \
            --stack-name "$stack_name" \
            --profile "$PROFILE" \
            --region "$REGION" \
            --query 'Stacks[0].StackStatus' \
            --output text 2>/dev/null)

        if [[ "$stack_status" == *"DELETE_IN_PROGRESS"* ]]; then
            echo "⏳ Stack is already being deleted. Waiting for completion..."
        elif [[ "$stack_status" == *"DELETE_COMPLETE"* ]]; then
            echo "✅ Stack is already deleted"
            return 0
        else
            # Delete the stack
            if aws cloudformation delete-stack \
                --stack-name "$stack_name" \
                --profile "$PROFILE" \
                --region "$REGION"; then
                echo "⏳ Waiting for $description deletion to complete..."
            else
                echo "❌ Failed to initiate deletion of $description"
                return 1
            fi
        fi

        # Wait for stack deletion to complete (with timeout)
        echo "   Waiting for stack deletion (this may take several minutes)..."
        if aws cloudformation wait stack-delete-complete \
            --stack-name "$stack_name" \
            --profile "$PROFILE" \
            --region "$REGION" \
            --cli-read-timeout 1800 \
            --cli-connect-timeout 60; then
            echo "✅ $description deleted successfully"
        else
            echo "❌ Failed to delete $description or deletion timed out"
            echo "   Check the CloudFormation console for more details"
            return 1
        fi
    else
        echo "⚠️  Stack '$stack_name' does not exist or is already deleted"
    fi
    echo ""
}

# Check which stacks exist
echo "🔍 Checking existing stacks..."
existing_stacks=()
for stack_info in "${stacks[@]}"; do
    IFS=':' read -r stack_name description <<< "$stack_info"
    if stack_exists "$stack_name"; then
        existing_stacks+=("$stack_info")
        echo "  ✓ $stack_name exists"
    else
        echo "  - $stack_name (not found)"
    fi
done
echo ""

# Exit if no stacks to delete
if [[ ${#existing_stacks[@]} -eq 0 ]]; then
    echo "✅ No stacks found to delete!"
    exit 0
fi

# Show what will be deleted
echo "🚨 WARNING: This will delete the following stacks:"
for stack_info in "${existing_stacks[@]}"; do
    IFS=':' read -r stack_name description <<< "$stack_info"
    echo "  🗑️  $stack_name ($description)"
done
echo ""
echo "⚠️  This action is IRREVERSIBLE!"
echo "⚠️  All resources in these stacks will be permanently deleted!"
echo ""


# Delete stacks in reverse order
echo "🚀 Starting stack deletion process..."
echo ""

failed_deletions=()
for stack_info in "${existing_stacks[@]}"; do
    IFS=':' read -r stack_name description <<< "$stack_info"
    if ! delete_stack "$stack_name" "$description"; then
        failed_deletions+=("$stack_name")
    fi
done

# Summary
echo "📊 Deletion Summary:"
echo "✅ Successfully deleted: ${#successful_deletions[@]} stack(s)"
if [[ ${#successful_deletions[@]} -gt 0 ]]; then
    for stack in "${successful_deletions[@]}"; do
        echo "  ✓ $stack"
    done
fi

if [[ ${#failed_deletions[@]} -gt 0 ]]; then
    echo ""
    echo "❌ Failed to delete: ${#failed_deletions[@]} stack(s)"
    for stack in "${failed_deletions[@]}"; do
        echo "  ✗ $stack"
    done
    echo ""
    echo "💡 Troubleshooting tips:"
    echo "  1. Check if S3 buckets need to be emptied manually"
    echo "  2. Check for resources with DeletionPolicy: Retain"
    echo "  3. Look for cross-stack references preventing deletion"
    echo "  4. Check CloudFormation console for detailed error messages"
    echo ""
    echo "🔗 Check stack events:"
    for stack in "${failed_deletions[@]}"; do
        echo "  aws cloudformation describe-stack-events --stack-name $stack --profile $PROFILE --region $REGION"
    done
    echo ""
    exit 1
else
    echo ""
    echo "🎉 All stacks have been successfully deleted!"
fi