# Infra Stacks 

## General
In this project, we will focus on the implementation of various Infrastructure as Code (IaC) tools, 
to provision and manage infrastructure resources. The objective of this project is to gain hands-on experience with IaC 
practices, enhance our understanding of cloud infrastructure provisioning, and streamline the deployment process.

## Architecture design
![Optional Image Alt Text](docs/architecture_v2.svg)


### Terraform
Available under directory ./terraform

To set up stack in AWS:
```bash
terraform -chdir=./terraform init
terraform -chdir=./terraform apply -auto-approve
```

To destroy stack:
```bash
terraform -chdir=./terraform destroy 
```

how to build docker image 
```bash
export AWS_PROFILE=profile
aws sso login

docker/build.sh
docker/tag.sh
docker/login.sh
docker/push.sh
```