import json
import string
from typing import Dict

import pulumi
import pulumi_aws as aws
from naming_utils import get_resource_name
from pulumi_random import RandomPassword

HTTP_METHODS = ["GET", "PUT"]
ENDPOINTS = {"orders": "orders", "customers": "customers"}
STAGE_NAME = "prod"


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
            opts=pulumi.ResourceOptions(parent=self),
        )

        api_password_secret = aws.secretsmanager.Secret(
            get_resource_name("api-token-secret", env),
            name=f"api-token-secret-{env}",
            description="API Gateway authorisation token",
            tags={"Name": get_resource_name("api-token-secret", env)},
            opts=pulumi.ResourceOptions(parent=self),
        )

        api_password_secret_version = aws.secretsmanager.SecretVersion(
            resource_name=get_resource_name("api-token-authorisation-version", env),
            secret_id=api_password_secret.id,
            secret_string=api_password.result.apply(
                lambda pwd: json.dumps({"password": pwd})
            ),
            opts=pulumi.ResourceOptions(parent=api_password_secret),
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
            region, account_id, api_password_secret.arn, rds_secret_arn
        ).apply(
            lambda args: json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            "Resource": [f"arn:aws:logs:{args[0]}:{args[1]}:*"],
                        },
                        {
                            "Effect": "Allow",
                            "Action": [
                                "secretsmanager:GetSecretValue",
                                "secretsmanager:DescribeSecret",
                            ],
                            "Resource": [
                                args[2],  # api_password_secret.arn
                                args[3],  # rds_secret_arn
                            ],
                        },
                        {
                            "Effect": "Allow",
                            "Action": [
                                "rds-db:connect",
                                "rds:DescribeDBInstances",
                                "rds-data:ExecuteStatement",
                            ],
                            "Resource": ["*"],
                        },
                        {
                            "Effect": "Allow",
                            "Action": ["lambda:InvokeFunction"],
                            "Resource": ["*"],
                        },
                    ],
                }
            )
        )

        lambda_policy = aws.iam.Policy(
            get_resource_name("lambda-rest-api-policy", env),
            policy=lambda_iam_policy,
            opts=pulumi.ResourceOptions(parent=lambda_role),
        )

        aws.iam.RolePolicyAttachment(
            get_resource_name("lambda-rest-api-policy-attach", env),
            role=lambda_role.name,
            policy_arn=lambda_policy.arn,
            opts=pulumi.ResourceOptions(parent=lambda_role),
        )

        def create_lambda_function(
            name: str,
            code_path: str,
            env_vars: Dict[str, pulumi.Input[str]],
            layers=None,
        ):
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
            layers,
        )

        lambda_token_authorizer = create_lambda_function(
            "lambda-token-authorizer",
            "lambda_grant_token_access",
            {"SECRET_NAME": api_password_secret.name},
            layers=None,
        )

        # Create API Gateway REST API
        rest_api = aws.apigateway.RestApi(
            resource_name=get_resource_name("Rest-Api", env),
            name=get_resource_name("Rest-Api", env),
            endpoint_configuration={"types": "REGIONAL"},
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Allow API Gateway to invoke token authorizer
        lambda_permission = aws.lambda_.Permission(
            get_resource_name("invoke-token-authorizer", env),
            action="lambda:InvokeFunction",
            function=lambda_token_authorizer.name,
            principal="apigateway.amazonaws.com",
            source_arn=rest_api.execution_arn.apply(lambda arn: f"{arn}/*/*"),
            opts=pulumi.ResourceOptions(parent=self),
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
            opts=pulumi.ResourceOptions(parent=rest_api),
            authorizer_result_ttl_in_seconds=0,
        )
        uri_lambda_rest_api = pulumi.Output.concat(
            "arn:aws:apigateway:",
            aws.config.region,
            ":lambda:path/2015-03-31/functions/",
            lambda_rest_api.arn,
            "/invocations",
        )
        # --- API Gateway Resources & Methods ---
        resources = {}
        for key, path in ENDPOINTS.items():
            resources[key] = aws.apigateway.Resource(
                f"{key}Resource",
                rest_api=rest_api.id,
                parent_id=rest_api.root_resource_id,
                path_part=path,
            )

        # === Methods + Integrations ===
        http_methods = ["GET", "PUT"]

        methods = {}
        integrations = {}

        for key, resource in resources.items():
            for method in http_methods:
                method_name = f"{key}-{method}"

                api_method = aws.apigateway.Method(
                    method_name,
                    rest_api=rest_api.id,
                    resource_id=resource.id,
                    http_method=method,
                    authorization="CUSTOM",
                    authorizer_id=authorizer.id,
                    request_parameters={
                        "method.request.header.Authorization": True,
                        **(
                            {"method.request.querystring.customer_id": False}
                            if key == "customers"
                            else {}
                        ),
                        **(
                            {"method.request.querystring.order_id": False}
                            if key == "orders"
                            else {}
                        ),
                    },
                )
                methods[method_name] = api_method

                integration = aws.apigateway.Integration(
                    f"{method_name}-integration",
                    rest_api=rest_api.id,
                    resource_id=resource.id,
                    http_method=api_method.http_method,
                    integration_http_method="POST",
                    type="AWS_PROXY",
                    uri=uri_lambda_rest_api,
                )

                integrations[method_name] = integration

                aws.apigateway.MethodResponse(
                    f"{method_name}-response",
                    rest_api=rest_api.id,
                    resource_id=api_method.resource_id,
                    http_method=api_method.http_method,
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                    },
                    response_models={"application/json": "Empty"},
                )
                print("DEBUG integration type:", type(integration))

                aws.apigateway.IntegrationResponse(
                    f"{method_name}-integrationResponse",
                    rest_api=rest_api.id,
                    resource_id=api_method.resource_id,
                    http_method=api_method.http_method,
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                    },
                    opts=pulumi.ResourceOptions(depends_on=[integration]),
                )
                perm_name = get_resource_name(f"{key}-{method}-lambda-permission", env)

                aws.lambda_.Permission(
                    perm_name,
                    action="lambda:InvokeFunction",
                    function=lambda_rest_api.name,
                    principal="apigateway.amazonaws.com",
                    source_arn=rest_api.execution_arn.apply(
                        lambda arn, m=method, p=key: f"{arn}/*/{m}/{p}"
                    ),
                )

        # Deployment after all methods exist
        deployment = aws.apigateway.Deployment(
            get_resource_name("deployment", env),
            rest_api=rest_api.id,
            opts=pulumi.ResourceOptions(depends_on=list(integrations.values())),
        )

        aws.apigateway.Stage(
            get_resource_name("rest-api-stage", env),
            rest_api=rest_api.id,
            deployment=deployment.id,
            stage_name=STAGE_NAME,
            opts=pulumi.ResourceOptions(parent=rest_api, depends_on=[deployment]),
        )

        # --- Outputs ---
        pulumi.export(
            "RestApiEndpoint",
            pulumi.Output.concat(
                "https://",
                rest_api.id,
                f".execute-api.{region}.amazonaws.com/{STAGE_NAME}/",
            ),
        )
        pulumi.export("ApiPasswordSecretName", api_password_secret.name)
