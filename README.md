# Infra Stacks 

## General
In this project, we will focus on the implementation of various Infrastructure as Code (IaC) tools, 
to provision and manage infrastructure resources. The objective of this project is to gain hands-on experience with IaC 
practices, enhance our understanding of cloud infrastructure provisioning, and streamline the deployment process.

## Architecture design
![Optional Image Alt Text](docs/architecture_v2.svg)



##  Terraform AWS Workspace Configuration Script
This script `./run-terraform.sh` automates the setup of AWS and Terraform configurations, 
simplifying the management of infrastructure with specific AWS profiles and Terraform workspaces.

### Prerequisites
Before running this script, ensure the following prerequisites are met:

- AWS CLI installed and configured on your system.
- Terraform installed and accessible from your command line.
- An AWS profile set up on your machine that the script can utilize.

### Script Parameters
The script accepts two mandatory command-line arguments:

`-p, --profile` : Specifies the AWS profile to be used for AWS operations. 

`-w, --workspace`: Defines the Terraform workspace to be used or created for managing resources.

```bash
chmod +x run-terraform.sh 
./run-terraform.sh -p <aws_profile> -w <workspace_name>
```

This script is intended for use by developers and administrators who manage AWS resources and Terraform 
configurations. It streamlines the process by automating initial setup tasks, workspace management, 
and resource deployment.
