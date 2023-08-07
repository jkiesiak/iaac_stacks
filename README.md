### Stacks have been implemented to show off 

# infra_stacks
In this project, we will be focusing on the implementation of different Infrastructure as Code tools, 
specifically Terraform, to provision and manage infrastructure resources. 
The objective of this project is to gain hands-on experience with IaC practices, 
enhance your understanding of cloud infrastructure provisioning, and streamline the deployment process.

To set up stack in AWS:
```bash
terraform -chdir=./terraform init
terraform -chdir=./terraform apply -auto-approve
```

To destroy stack:
```bash
terraform -chdir=./terraform destroy 
```

