#!/bin/bash

export AWS_PROFILE=user_infra
echo $AWS_PROFILE

export WORKSPACE=test
export AWS_DEFAULT_REGION=eu-west-1
echo $AWS_DEFAULT_REGION
echo "-----------------------------"
terraform workspace select $WORKSPACE
terraform destroy -auto-approve
