This :

Set the AWS profile and region

Run pip install -r requirements.txt (if required)

Run cdk bootstrap

Run cdk synth

Run cdk deploy

./deploy_cdk.sh -p user_infra -e dev
cdk destroy --all --require-approval never --context env="dev" --profile "user_infra"