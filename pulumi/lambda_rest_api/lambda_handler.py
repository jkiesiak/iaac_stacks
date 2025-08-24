import boto3
import os
import json
import logging
import pg8000
from decimal import Decimal
import datetime

_cached_token = None

# Environment variables
SECRET_NAME = os.getenv("SECRET_NAME")
RDS_SECRET_NAME = os.getenv("RDS_SECRET_NAME")
REGION = str(os.getenv("REGION", "eu-west-1"))
DB_NAME = str(os.getenv("DB_NAME", "database_rds"))
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


def validate_update_fields(update_fields):
    """Validate field types and values before update"""
    valid_fields = {
        "first_name": str,
        "last_name": str,
        "email": str,
        "phone": str,
        "address": str
    }

    for field, value in update_fields.items():
        if field not in valid_fields:
            raise ValueError(f"Invalid field: {field}")
        if not isinstance(value, valid_fields[field]):
            raise ValueError(f"Invalid type for {field}. Expected {valid_fields[field]}")

def get_customer_data(customer_id):
    """Fetch customer data from PostgreSQL database."""
    query = f"""
        SELECT customer_id, first_name, last_name, email, phone, address
        FROM {DB_SCHEMA}.customers
        WHERE customer_id = %s
    """
    result = query_db(query, (customer_id,))
    result = result[0]
    columns = ["customer_id", "first_name", "last_name", "email", "phone", "address"]

    logger.info(f"Customer: raw result type: {type(result)}, content: {result}")

    return dict(zip(columns, result))


def update_customer_data(customer_id, update_fields):
    """Update customer data with proper transaction handling"""
    logger.info(f"Update update_fields: {update_fields}")
    allowed_fields = {"first_name", "last_name", "email", "phone", "address"}
    update_fields = {k: v for k, v in update_fields.items() if k in allowed_fields}

    db_details = get_db_credentials(RDS_SECRET_NAME)
    conn = None
    try:
        conn = pg8000.connect(
            user="postgres",
            password=db_details["password"],
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        cursor = conn.cursor()

        set_clause = ", ".join(f"{key} = %s" for key in update_fields.keys())
        values = list(update_fields.values()) + [customer_id]

        query = f"""
            UPDATE {DB_SCHEMA}.customers
            SET {set_clause}
            WHERE customer_id = %s
            RETURNING customer_id
        """

        cursor.execute(query, values)
        result = cursor.fetchone()
        conn.commit()  # Explicit commit

        return bool(result)

    except Exception as e:
        if conn:
            conn.rollback()  # Critical for data consistency
        logger.error(f"Update failed: {str(e)}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


def get_order_data(order_id):
    """Fetch order details from PostgreSQL database."""
    query = f"""
        SELECT order_id, order_date, total_amount, customer_id
        FROM {DB_SCHEMA}.orders 
        WHERE order_id = %s
    """
    result = query_db(query, (order_id,))

    if not result:
        logger.info(f"Order with order_id = {order_id} not found")
        return None

    columns = ["order_id", "order_date", "total_amount", "customer_id"]
    row = result[0]
    order_dict = dict(zip(columns, row))

    # Convert non-JSON types
    converted_dict = {}
    for key, value in order_dict.items():
        if isinstance(value, Decimal):
            converted_dict[key] = float(value)
        elif isinstance(value, datetime.date):
            converted_dict[key] = value.isoformat()
        else:
            converted_dict[key] = value

    logger.info(f"Order: converted data: {converted_dict}")
    return converted_dict

def validate_token(token):
    global _cached_token
    if not token or not isinstance(token, str):
        return False

    try:
        if _cached_token is None:
            _cached_token = get_db_credentials(SECRET_NAME)["password"]
        return token == _cached_token
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return False

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        http_method = event.get("httpMethod")
        params = event.get("queryStringParameters") or {}
        headers = event.get("headers") or {}

        token = headers.get("Authorization")
        if not validate_token(token):
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        if http_method == "GET":
            if "customer_id" in params:
                customer_data = get_customer_data(params["customer_id"])
                if customer_data:
                    return {"statusCode": 200, "body": json.dumps(customer_data)}
                return {"statusCode": 404, "body": json.dumps({"error": "Customer not found"})}

            elif "order_id" in params:
                order_data = get_order_data(params["order_id"])
                if order_data:
                    return {"statusCode": 200, "body": json.dumps(order_data)}
                return {"statusCode": 404, "body": json.dumps({"error": "Order not found"})}

            else:
                return {"statusCode": 400, "body": json.dumps({"error": "Missing query parameters"})}


        elif http_method == "PUT":

            try:

                body = json.loads(event["body"])

                customer_id = body.get("customer_id")

                update_fields = {k: v for k, v in body.items() if k != "customer_id"}

                validate_update_fields(update_fields)
                updated = update_customer_data(customer_id, update_fields)

                if updated:
                    return {
                        "statusCode": 200,
                        "body": json.dumps({
                            "message": "Customer updated",
                            "customer_id": customer_id
                        })
                    }

                return {"statusCode": 404, "body": json.dumps({"error": "Customer not found"})}

            except json.JSONDecodeError:
                return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON"})}

            except ValueError as ve:
                return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

        else:
            return {"statusCode": 405, "body": json.dumps({"error": f"Method {http_method} not allowed"})}

    except Exception as e:
        logger.error(f"Error in Lambda handler: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error, check the logs"})}
