import json
import random
import string
from typing import Dict
from pulumi_random import RandomPassword

import pulumi
import pulumi_aws as aws
from naming_utils import get_resource_name

HTTP_METHODS = ["GET", "PUT"]
ENDPOINTS = {"orders": "/orders", "customers": "/customers"}
STAGE_NAME = "prod"
PASSWORD_CHARS = string.ascii_letters + string.digits + "_%@"

class ApiGatewayStack(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        env: str,
        rds_secret_name: str,
        rds_endpoint_address: str,
        rds_secret_arn: str,
        pg8000_layer_arn: str,
        logging_layer_arn: str,
        opts: pulumi.ResourceOptions = None,
    ):
        super().__init__("custom:ApiGatewayStack", name, None, opts)

        self.env = env

        account_id = aws.get_caller_identity().account_id
        region = aws.config.region
        layers = [pg8000_layer_arn, logging_layer_arn]

        api_password = RandomPassword(
            get_resource_name("api-token", env),
            length=16,
            special=False,
            override_special="_%@",
            opts=pulumi.ResourceOptions(parent=self)
        )

        api_password_secret = aws.secretsmanager.Secret(
            get_resource_name("api-token-secret", env),
            description="API Gateway authorisation token",
            tags={"Name": get_resource_name("api-token-secret", env)},
            opts=pulumi.ResourceOptions(parent=self)
        )

        api_password_secret_version = aws.secretsmanager.SecretVersion(
            resource_name=get_resource_name("api-token-authorisation-version", env),
            secret_id=api_password_secret.id,
            secret_string=api_password.result.apply(lambda pwd: json.dumps({"password": pwd})),
            opts=pulumi.ResourceOptions(parent=api_password_secret),
        )

        # Create API Gateway REST API
        rest_api = aws.apigateway.RestApi(
            resource_name=get_resource_name("Rest-Api", env),
            name=get_resource_name("Rest-Api", env),
            endpoint_configuration=aws.apigateway.RestApiEndpointConfigurationArgs(
                types=["REGIONAL"]
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Create Lambda Execution Role with necessary permissions
        lambda_role = aws.iam.Role(
            resource_name=get_resource_name("lambda_rest_api", env),
            assume_role_policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": [
                                    "lambda.amazonaws.com",
                                    "apigateway.amazonaws.com",
                                ]
                            },
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        lambda_iam_policy = pulumi.Output.all(
            region,
            account_id,
            api_password_secret.arn,
            rds_secret_arn
        ).apply(lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    "Resource": [
                        f"arn:aws:logs:{args[0]}:{args[1]}:*"
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret"
                    ],
                    "Resource": [
                        args[2],  # api_password_secret.arn
                        args[3],  # rds_secret_arn
                    ],
                },
                {
                    "Effect": "Allow",
                    "Action": ["rds-db:connect", "rds:DescribeDBInstances", "rds-data:ExecuteStatement"],
                    "Resource": ["*"],
                },
                {
                    "Effect": "Allow",
                    "Action": ["lambda:InvokeFunction"],
                    "Resource": ["*"],
                },
            ],
        }))


        lambda_policy = aws.iam.Policy(
            get_resource_name("lambda-rest-api-policy", env),
            policy=lambda_iam_policy,
            opts=pulumi.ResourceOptions(parent=lambda_role)
        )

        aws.iam.RolePolicyAttachment(
            get_resource_name("lambda-rest-api-policy-attach", env),
            role=lambda_role.name,
            policy_arn=lambda_policy.arn,
            opts=pulumi.ResourceOptions(parent=lambda_role)
        )
        def create_lambda_function(name: str, code_path: str, env_vars: Dict[str, pulumi.Input[str]], layers=None):
            return aws.lambda_.Function(
                resource_name=get_resource_name(name, env),
                name=f"{name}-{env}",
                role=lambda_role.arn,
                runtime="python3.9",
                handler="lambda_handler.lambda_handler",
                code=pulumi.AssetArchive({"./": pulumi.FileArchive(code_path)}),
                environment=aws.lambda_.FunctionEnvironmentArgs(variables=env_vars),
                layers=layers or [],
                opts=pulumi.ResourceOptions(parent=self),
            )

        # Create main Lambda function for REST API
        lambda_rest_api = create_lambda_function(
            "lambda_rest_api",
            "lambda_rest_api",
            {
                "SECRET_NAME": api_password_secret.name,
                "RDS_SECRET_NAME": rds_secret_name,
                "DB_HOST": rds_endpoint_address,
            },
            layers
        )

        lambda_token_authorizer = create_lambda_function(
            "lambda-token-authorizer",
            "lambda_grant_token_access",
            {"SECRET_NAME": api_password_secret.name},
            layers=None
        )

        # Allow API Gateway to invoke token authorizer
        lambda_permission = aws.lambda_.Permission(
            get_resource_name("invoke-token-authorizer", env),
            action="lambda:InvokeFunction",
            function=lambda_token_authorizer.name,  # or .arn; .name is fine
            principal="apigateway.amazonaws.com",
            source_arn=rest_api.execution_arn.apply(lambda arn: f"{arn}/*/*"),
            opts=pulumi.ResourceOptions(parent=self)
        )

        aws.lambda_.Permission(
            get_resource_name("allow-apigw-invoke-rest-lambda", env),
            action="lambda:InvokeFunction",
            function=lambda_rest_api.name,
            principal="apigateway.amazonaws.com",
            source_arn=rest_api.execution_arn.apply(lambda arn: f"{arn}/*/*"),
            opts=pulumi.ResourceOptions(parent=self)
        )

        authorizer_uri = lambda_token_authorizer.arn.apply(
            lambda arn: f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{arn}/invocations"
        )

        authorizer = aws.apigateway.Authorizer(
            get_resource_name("custom-authorizer", env),
            name=get_resource_name("custom-authorizer", env),
            rest_api=rest_api.id,
            authorizer_uri=authorizer_uri,
            identity_source="method.request.header.Authorization",
            type="TOKEN",
            opts=pulumi.ResourceOptions(parent=rest_api)
        )

        # --- API Gateway Resources & Methods ---
        method_resources = []
        integration_resources = []

        for key, path in ENDPOINTS.items():
            resource = aws.apigateway.Resource(
                get_resource_name(f"resource-{key}", env),
                rest_api=rest_api.id,
                parent_id=rest_api.root_resource_id,
                path_part=key,
                opts=pulumi.ResourceOptions(parent=rest_api)
            )

            for method in HTTP_METHODS:
                request_params = {"method.request.header.Authorization": True}
                if key == "customers":
                    request_params["method.request.querystring.customer_id"] = False
                elif key == "orders":
                    request_params["method.request.querystring.order_id"] = False

                method_res = aws.apigateway.Method(
                    get_resource_name(f"method-{key}-{method}", env),
                    rest_api=rest_api.id,
                    resource_id=resource.id,
                    http_method=method,
                    authorization="CUSTOM",
                    authorizer_id=authorizer.id,
                    request_parameters=request_params,
                    opts=pulumi.ResourceOptions(parent=resource)
                )
                uri = pulumi.Output.all(region, lambda_rest_api.arn).apply(
                    lambda args: f"arn:aws:apigateway:{args[0]}:lambda:path/2015-03-31/functions/{args[1]}/invocations"
                )
                integration_res = aws.apigateway.Integration(
                    get_resource_name(f"integration-{key}-{method}", env),
                    rest_api=rest_api.id,
                    resource_id=resource.id,
                    http_method=method,  # must match the Method's HTTP method
                    integration_http_method="POST",  # for Lambda proxy
                    type="AWS_PROXY",
                    uri=uri,
                    passthrough_behavior="WHEN_NO_MATCH",
                    opts=pulumi.ResourceOptions(parent=resource, depends_on=[method_res])
                )

                method_resources.append(method_res)
                integration_resources.append(integration_res)

        # Deployment after all methods exist
        deployment = aws.apigateway.Deployment(
            get_resource_name("rest-api-deployment", env),
            rest_api=rest_api.id,
            opts=pulumi.ResourceOptions(parent=rest_api, depends_on=integration_resources)
        )

        aws.apigateway.Stage(
            get_resource_name("rest-api-stage", env),
            rest_api=rest_api.id,
            deployment=deployment.id,
            stage_name=STAGE_NAME,
            opts=pulumi.ResourceOptions(parent=rest_api, depends_on=integration_resources)
        )

        # --- Outputs ---
        pulumi.export("RestApiEndpoint",
            pulumi.Output.concat("https://", rest_api.id, f".execute-api.{region}.amazonaws.com/{STAGE_NAME}/")
        )
        pulumi.export("ApiPasswordSecretName", api_password_secret.name)
        pulumi.export("integration_uri_example", pulumi.Output.all(region, lambda_rest_api.arn)
              .apply(lambda args: f"arn:aws:apigateway:{args[0]}:lambda:path/2015-03-31/functions/{args[1]}/invocations"))
