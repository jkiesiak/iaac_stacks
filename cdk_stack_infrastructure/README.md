This :

Set the AWS profile and region

Run pip install -r requirements.txt (if required)

Run cdk bootstrap

Run cdk synth

Run cdk deploy
```bash
./deploy_cdk.sh -p user_infra -e prod
cdk destroy --all --require-approval never --context env="dev" --profile "user_infra"
```

✅ Example Usage

Destroying stack:
```bash
./destroy-stacks.sh -p user_infra -e prod
```
