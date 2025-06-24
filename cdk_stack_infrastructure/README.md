This :

Set the AWS profile and region

Run pip install -r requirements.txt (if required)

Run cdk bootstrap

Run cdk synth

Run cdk deploy
```bash
./deploy_cdk.sh -p user_infra -e dev
cdk destroy --all --require-approval never --context env="dev" --profile "user_infra"
```

✅ Example Usage

Destroying stack:
```bash
./destroy.sh -p my-profile -e dev
./destroy.sh -p my-profile
```
