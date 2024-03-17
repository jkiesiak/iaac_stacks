#!/bin/bash

export AWS_PROFILE=
echo $AWS_PROFILE

export WORKSPACE=joa_test4
#export AWS_DEFAULT_REGION=eu-west-1
#echo $AWS_DEFAULT_REGION

echo "-----------------------------"
terraform -chdir=./terraform init
terraform -chdir=./terraform workspace new $WORKSPACE
terraform -chdir=./terraform workspace select $WORKSPACE
terraform -chdir=./terraform fmt
terraform -chdir=./terraform apply -auto-approve -var is_development=true
