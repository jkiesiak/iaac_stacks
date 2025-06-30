# Infrastructure as Code (IaC) Implementation Project

## Table of Contents
1. [General Overview](#general-overview)
2. [Architecture](#architecture)
    - [Diagram](#diagram)
    - [Resources Used](#resources-used)
    - [Core Functionalities](#core-functionalities)
4. [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Permissions for Script Execution](#permissions-for-script-execution)
    - [Deployment of Resources](#deployment-of-resources)
    - [Clean-Up of Provisioned Resources](#clean-up-of-provisioned-resources)
5. [Usage Examples](#usage-examples)
6. [Monitoring and Debugging](#monitoring-and-debugging)
7. [Contributions](#contributions)
8. [License](#license)


## General overview
Infrastructure as Code (IaC) is a practice for managing and provisioning cloud resources automatically through code, 
enabling efficient, scalable, and repeatable deployments. This project aims to implement an IaC solution using various 
technologies to deploy and manage cloud resources effectively. The primary objective is to gain hands-on experience with 
different IaC tools, including Terraform and AWS CDK, and to compare their features, usability, and performance. 
By implementing the same architecture across these technologies, the project evaluates their strengths, differences, 
and suitability for managing cloud infrastructure.

## Architecture
### Diagram
The following diagram illustrates the architecture:
![Optional Image Alt Text](docs/architecture_v3.svg)

### Resources Used
The architecture consists of a serverless, event-driven system deployed on AWS, utilizing the following resources:
- **Amazon S3**: Two buckets are used—one event bucket for receiving JSON files and one backup bucket serving as 
a destination for processed data.
- **AWS Lambda:**: Executes code for processing JSON data and performing database operations, triggered by events from 
the S3 bucket or Step Functions.
- **Amazon API Gateway**: Provides RESTful endpoints to access the system (`/customers`, `/orders`, `/orders/{id}`, 
`/customers/{id}`) for querying and modifying data.
- **AWS Step Functions**: Orchestrates the workflow for processing JSON files, coordinating Lambda functions and data movement.
- **Amazon RDS**: Stores structured data in a managed relational database for the application.
- **AWS Identity and Access Management (IAM)**: Manages secure access and permissions for Lambda functions etc

### Core Functionalities

The system is event-driven, with key functionalities implemented as follows:

1. Database Schema Configuration:
   - Terraform: Configures the RDS database schema using direct `psql` PostgreSQL commands, executing external sql script 
defining two tables with primary and foreign keys and creating a user with admin privileges.
   - AWS CDK: Uses an additional Lambda function to execute an external SQL script, setting up the same database schema 
with two tables and an admin user.
   - JSON: The Json is generated based on the CDK code, hence the architecture is the same and the functionalities. 

2. **Event-Driven Processing**: 
When a JSON file is uploaded to the event S3 bucket, it triggers an AWS Step Function. The Step Function orchestrates 
   a Lambda function that processes the JSON data and inserts it into the RDS database. After processing, the file is 
   moved to the backup S3 bucket for storage.

3. **Error Handling and File Management**:
If data insertion into the database fails, the file is explicitly moved to an "unprocessed" directory, ensuring 
the issue is logged for further investigation.

4. **API Gateway Endpoints**:
The API Gateway exposes four endpoints to interact with the RDS database:

GET `/customers`: Retrieves customer data.

GET `/orders`: Retrieves order data.

PUT `/orders/{id}`: Updates specific order data by ID.

PUT `/customers/{id}`: Updates specific customer data by ID.

5. **Robust Logging**:
Detailed logs capture all operations, providing developers with insights into system behavior and error causes.

   

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
./run-terraform.sh -p user_infra -w vol9
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

