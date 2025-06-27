# Basic usage
./deploy.sh -p user13

# With custom region
./deploy.sh -p user13 -r us-west-2

# Show help
./deploy.sh -h

# Error if no profile provided
./deploy.sh
# Output: Error: AWS profile is required!


# Basic usage with confirmation
./delete-stacks.sh -p user_infra

# Skip confirmation prompt
./delete-stacks.sh -p user13 -f

# Use different region
./delete-stacks.sh -p user13 -r us-east-1 -f

