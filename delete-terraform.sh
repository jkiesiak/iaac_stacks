#!/bin/bash

export AWS_PROFILE=
echo $AWS_PROFILE

export WORKSPACE=
export AWS_DEFAULT_REGION=eu-west-1
echo $AWS_DEFAULT_REGION
echo "-----------------------------"
terraform -chdir=./terraform workspace select $WORKSPACE
terraform -chdir=./terraform destroy -auto-approve
