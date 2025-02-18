import boto3
import os
import json
import logging
import pg8000
from decimal import Decimal
import datetime

# Environment variables
SECRET_NAME = os.getenv("SECRET_NAME")
RDS_SECRET_NAME = os.getenv("RDS_SECRET_NAME")
REGION = str(os.getenv("REGION", "eu-west-1"))
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_SCHEMA= "myschema1"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
        conn = pg8000.connect(
            user="postgres",
            password=db_details["password"],
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        conn.close()

        return [tuple(row) for row in result]
    except Exception as e:
        logger.error(f"Database query error: {e}")
        return None


def get_customer_data(customer_id):
    """Fetch customer data from PostgreSQL database."""
    query = f"""
        SELECT customer_id, first_name, last_name, email, phone, address
        FROM {DB_SCHEMA}.customers
        WHERE customer_id = %s
    """
    result = query_db(query, (customer_id,))
    logger.info(f"Customer: raw result type: {type(result)}, content: {result}")

    if not result:
        return None

    columns = ["customer_id", "first_name", "last_name", "email", "phone", "address"]
    return dict(zip(columns, result[0]))

def get_order_data(order_id):
    """Fetch order details from PostgreSQL database."""
    query = f"""
        SELECT order_id, order_date, total_amount, customer_id
        FROM {DB_SCHEMA}.orders 
        WHERE order_id = %s
    """

    result = query_db(query, (order_id,))
    if not result:
        logger.info(f"This customer_id = {order_id} doesn't exist in the db")
        return None
    logger.info(f"Customer: raw result type: {type(result)}, content: {result}")

    columns = ["order_id", "order_date", "total_amount", "customer_id"]

    row = result[0]
    order_dict = dict(zip(columns, row))

    def convert_data(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return obj

    json_order = json.dumps(order_dict, default=convert_data)
    logger.info(f"Order: JSON serialized data: {json_order}")

    return json.dumps(order_dict, default=convert_data)

def validate_token(token):
    """Validates the token using AWS Secrets Manager."""
    try:
        stored_password = get_db_credentials(SECRET_NAME)["password"]
        return token == stored_password
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return False


def lambda_handler(event, context):
    """Handles API Gateway requests for authentication and data retrieval."""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        headers = event.get("headers", {})
        token = headers.get("Authorization", "").strip()

        if not token or not validate_token(token):
            return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}

        params = event.get("queryStringParameters", {})
        logger.info(f"Received params: {json.dumps(params)}")

        if not params:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing query parameters"})}

        # Handle customer request
        if "customer_id" in params:
            customer_data = get_customer_data(params["customer_id"])
            if customer_data:
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps(customer_data)
                }
            return {"statusCode": 404, "body": json.dumps({"error": "Customer not found"})}

        # Handle order request
        if "order_id" in params:
            order_data = get_order_data(params["order_id"])
            if order_data:
                return order_data
            return {"statusCode": 404, "body": json.dumps({"error": "Order not found"})}


    except Exception as e:
        logger.error(f"Error in Lambda handler: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}
