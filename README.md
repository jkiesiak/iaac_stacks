# Infra Stacks 

## General
In this project, we will focus on the implementation of various Infrastructure as Code (IaC) tools, 
to provision and manage infrastructure resources. The objective of this project is to gain hands-on experience with IaC 
practices, enhance our understanding of cloud infrastructure provisioning, and streamline the deployment process.

## Architecture design
![Optional Image Alt Text](docs/architecture_v2.svg)

# TODO: add explanation

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
./run-terraform.sh -p user_infra -w vol4
```

This script is intended for use by developers and administrators who manage AWS resources and Terraform 
configurations. It streamlines the process by automating initial setup tasks, workspace management, 
and resource deployment.



Implemented functionalities


The schema is set up using psql cmd with schema of database.

Lambda which preprocesses data 

The initial implementation moves files to the unprocessed directory in two scenarios:

When the data insertion fails: The file is explicitly moved to the unprocessed directory after detecting a failure during the insertion step.
When an exception occurs: If any unexpected error occurs (e.g., a parsing issue, missing data, or S3 error), the file is also moved to the unprocessed directory.
The reason for handling these scenarios separately was to ensure clarity in the logging and to avoid unintended behavior if future adjustments need different actions based on failure cause. However, I agree that it could be simplified to avoid repetitive calls for moving the file.

Here’s the simplified solution that moves the file to the correct directory in one place, while keeping the logic clean:


