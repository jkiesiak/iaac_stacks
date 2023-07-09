# infra_stacks

To set up stack in AWS
```
terraform -chdir=./terraform apply -var-file="variables.tfvars" -auto-approve
```
flag -auto-approve approves run to execute in cloud.

To destroy stack:
```
terraform -chdir=./terraform destroy -var-file=variables.tfvars -auto-approve

```
