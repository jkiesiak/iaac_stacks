# Infrastructure as Code (IaC) Implementation Project

## Table of Contents
1. [General Overview](#general-overview)
2. [Architecture](#architecture)
    - [Resources Used](#resources-used)
    - [Core Functionalities](#core-functionalities)
3. [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Permissions for Script Execution](#permissions-for-script-execution)
    - [Deployment of Resources](#deployment-of-resources)
    - [Clean-Up of Provisioned Resources](#clean-up-of-provisioned-resources)
5. [Usage Examples](#usage-examples)
6. [Monitoring and Debugging](#monitoring-and-debugging)
7. [Contributions](#contributions)
8. [License](#license)


## General overview
This repository provides a comprehensive implementation of various Infrastructure as Code (IaC) tools to provision and 
manage infrastructure resources efficiently and effectively. The primary objective of this project is to gain hands-on 
experience with IaC practices, enhance our understanding of cloud infrastructure provisioning, and streamline deployment 
processes.

## Architecture
![Optional Image Alt Text](docs/architecture_v2.svg)

### Resources Used
- **AWS Lambda**: Executes code for data processing and triggers actions based on events.
- **Amazon RDS**: Stores structured data for applications.
- **Amazon S3**: Serves as a backup destination for critical data.
- **Amazon API Gateway**: Provides RESTful endpoints to access the system (`/order`, `/customer`).
- **AWS Identity and Access Management (IAM)**: Manages secure access and permissions for resources.
- **Amazon CloudWatch**: Monitors and logs system performance and activity.

### Core Functionalities

This project implements a variety of functionalities to ensure efficient and automated processing of data. 
Below are the core functionalities:

1. **Database Schema Setup**:
   - The database schema is initialized using `psql` commands with a predefined schema structure.

2. **Data Preprocessing with AWS Lambda**:
   - AWS Lambda functions preprocess incoming data before insertion into the database.
   - Includes validation, transformation, and error detection steps to ensure data integrity.
   - All inserted files are stored in the directory "backup".

3. **Error Handling and File Management**:
     If data insertion into the database fails, the file is explicitly moved to an "unprocessed" directory, ensuring the issue is logged for further investigation.

4. **Streamlined File Movement Logic**:
   - To reduce redundancy, the file movement process is now streamlined:
     - A single function handles moving files to the correct directory after detecting an error or exception.
     - This ensures clean and efficient code while maintaining detailed logging for debugging purposes.
   - The improved logic simplifies future adjustments by centralizing the handling of failed files, avoiding repetitive code.

5. **Robust Logging**:
   - Detailed logs capture all operations, providing developers with insights into system behavior and error causes.



## Getting started
To ensure a consistent, automated, and repeatable deployment of the infrastructure, two scripts are available:

- `./run-terraform.sh` : This bash script runs the terraform configuration and deploys necessary resources
- `./delete-terraform.sh` : this script safely destroys the provisioned resources in cloud


### Prerequisites
Before running the automation scripts or deploying the infrastructure, ensure the following prerequisites are met:

- AWS CLI installed and configured on your system.
- Terraform installed and accessible from your command line.
- An AWS profile set up on your machine that the script can utilize.

### Permissions for script execution

Before using the provided bash script, ensure that you have the necessary permissions to execute it. Use the `chmod` 
command to grant execute permissions if needed:
```bash
chmod +x run-terraform.sh
```

### Deployment of resources
The script accepts two mandatory command-line arguments:

`-p, --profile` : Specifies the AWS profile to be used for AWS authentication. 

`-w, --workspace`: Defines the Terraform workspace to be used or created for managing resources.

```bash
./run-terraform.sh -p <aws_profile> -w <workspace_name>
```

### Clean up of provisioned resources
The delete-terraform.sh script automates the cleanup process. This script ensures that all provisioned resources are 
safely and efficiently destroyed, avoiding any manual intervention. 
It helps maintain a clean environment by removing associated resources and preventing unintended costs.

```bash
./delete-terraform.sh
```

Safety precautions:
To avoid accidental deletion of critical resources, the script requires manual updated to specific parameters before execution.
Please, update following values in a script:
- `aws_profile` : The AWS profile used for authentication 
- `workspace` : Defines the Terraform workspace associated to the provisioned resources

