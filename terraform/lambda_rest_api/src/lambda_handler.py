import boto3
import os
import json

# Environment variables
SECRET_NAME = os.getenv("SECRET_NAME")
REGION = os.getenv("REGION")

# Initialize Secrets Manager client
client = boto3.client("secretsmanager", region_name=REGION)

def get_db_password(secrets_client):
    try:
        response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        secret = json.loads(response['SecretString'])
        logger.info("Database secret retrieved successfully.")
        return secret['password']
    except Exception as e:
        logger.error(f"Error retrieving secret: {e}")
        raise

def lambda_handler(event, context):
    """Custom authorizer for API Gateway."""
    try:
        # Retrieve Authorization token from the request
        token = event["authorizationToken"]

        # Get the stored password from Secrets Manager
        stored_password = get_secret()

        # Validate the token
        if token == stored_password:
            return {
                "principalId": "user",
                "policyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "execute-api:Invoke",
                            "Effect": "Allow",
                            "Resource": event["methodArn"]
                        }
                    ]
                }
            }
        else:
            raise Exception("Unauthorized")
    except Exception as e:
        raise Exception("Unauthorized")
