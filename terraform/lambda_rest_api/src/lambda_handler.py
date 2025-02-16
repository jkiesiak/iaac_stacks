import boto3
import os
import json
import logging
import pg8000

# Environment variables
SECRET_NAME = os.getenv("SECRET_NAME")
RDS_SECRET_NAME = os.getenv("RDS_SECRET_NAME")
REGION = str(os.getenv("REGION", "eu-west-1"))
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Secrets Manager client
client = boto3.client("secretsmanager", region_name=REGION)

def get_db_credentials(NAME_SECRET):
    try:
        response = client.get_secret_value(SecretId=NAME_SECRET)
        secret = json.loads(response["SecretString"])
        logger.info("Database secret retrieved successfully.")
        return secret
    except Exception as e:
        logger.error(f"Error retrieving secret: {e}")
        raise



def query_db(query, params):
    """Connects to PostgreSQL and executes a query."""
    db_details = get_db_credentials(RDS_SECRET_NAME)

    try:
        # Connect to PostgreSQL
        conn = pg8000.native.Connection(
            user=db_details["username"],
            password=db_details["password"],
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )

        # Execute query
        result = conn.run(query, params)

        # Close connection
        conn.close()

        return result
    except Exception as e:
        logger.error(f"Database query error: {e}")
        return None


def get_customer_data(customer_id):
    """Fetch customer data from PostgreSQL database."""
    query = f"""
        SELECT customer_id, first_name, last_name, email, phone, address
        FROM {DB_SCHEMA}.customers
        WHERE customer_id = :1
    """
    result = query_db(query, (customer_id,))

    if not result:
        return None

    columns = ["customer_id", "first_name", "last_name", "email", "phone", "address"]
    return dict(zip(columns, result[0]))


def get_order_data(order_id):
    """Fetch order details from PostgreSQL database."""
    query = f"""
        SELECT o.order_id, o.order_date, o.total_amount, c.customer_id, c.first_name, c.last_name, c.email
        FROM {DB_SCHEMA}.orders o
        JOIN {DB_SCHEMA}.customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = :1
    """
    result = query_db(query, (order_id,))

    if not result:
        return None

    columns = ["order_id", "order_date", "total_amount", "customer_id", "first_name", "last_name", "email"]
    return dict(zip(columns, result[0]))


def generate_policy(effect, method_arn):
    """Generates an IAM policy for API Gateway."""
    return {
        "principalId": "user",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": method_arn
                }
            ]
        }
    }


def lambda_handler(event, context):
    """Handles API Gateway requests for authentication and data retrieval."""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        params = event.get("queryStringParameters", {})
        logger.info(f"Received params: {json.dumps(params)}")


        # Extract authorization token
        token = event.get("authorizationToken", "").strip()

        if not token:
            logger.warning("Authorization token missing")
            return generate_policy("Deny", event["methodArn"])

        # Get stored secret password
        stored_password = get_db_credentials(SECRET_NAME)["password"]

        logger.info(f"Received token: {token}")
        logger.info(f"Stored password: {stored_password}")

        # Validate token
        if token != stored_password:
            logger.warning("Unauthorized request: Invalid token")
            return generate_policy("Deny", event["methodArn"])

        # If valid token, return "Allow"
        logger.info("Authorization successful")
        # Handle API request logic if HTTP method is GET
        if event.get("httpMethod") == "GET":
            params = event.get("queryStringParameters", {})

            if "order_id" in params:
                order_data = get_order_data(params["order_id"])
                if not order_data:
                    return {"statusCode": 404, "body": json.dumps({"error": "Order not found"})}
                return {"statusCode": 200, "body": json.dumps(order_data)}

            return {"statusCode": 400, "body": json.dumps({"error": "Missing required parameters"})}

        return generate_policy("Allow", event["methodArn"])

    except Exception as e:
        logger.error(f"Error in Lambda handler: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}


