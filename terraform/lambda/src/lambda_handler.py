import os
import boto3
import pg8000
import json

# Environment variables
S3_BACKUP_DATA = os.environ.get("S3_BACKUP_DATA")
S3_EVENT_DATA = os.environ.get("S3_EVENT_DATA")
RDS_HOST = os.environ.get("RDS_HOST")
RDS_DB = os.environ.get("RDS_DB")
RDS_USER = "postgres"
RDS_PASSWORD = os.environ.get("RDS_PASSWORD")
SSM_NAME = os.environ.get("SSM_NAME")

def lambda_handler(event, context):
    # Connect to S3
    s3_client = boto3.client('s3')
    ssm_client = boto3.client('ssm')

    parameter = ssm_client.get_parameter(Name=SSM_NAME, WithDecryption=True)
    rds_password = parameter['Parameter']['Value']

    # List all objects in the bucket and process each JSON file
    object_list = s3_client.list_objects(Bucket=S3_EVENT_DATA)
    if 'Contents' in object_list:
        for obj in object_list['Contents']:
            file_name = obj['Key']
            if file_name.endswith('.json'):
                print(f"Processing file: {file_name}")

    response = s3_client.get_object(Bucket=S3_EVENT_DATA, Key=file_name)
    base_name, extension = file_name.split(".")
    target_key = f"{base_name}_copy.{extension}"
    print(f"Processing copy of file: {target_key}")

    # Copy the file to the backup S3 bucket
    copy_source = {
        'Bucket': S3_EVENT_DATA,
        'Key': file_name
    }
    s3_client.copy(copy_source, S3_BACKUP_DATA, target_key)
    print(f"Copy of data has been executed to bucket {S3_BACKUP_DATA}: filename {target_key}")

    conn = pg8000.connect(
        user=RDS_USER,
        password=rds_password,
        host=RDS_HOST,
        database=RDS_DB
    )

    # Insert data into RDS
    cursor = conn.cursor()
    try:
        file_content = response['Body'].read().decode('utf-8')
        data = json.loads(file_content)
        print(data)

        if 'customer' in file_name:
            insert_sql = """
                INSERT INTO myschema1.customers (customer_id, first_name, last_name, email, phone, address)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
            for customer in data:
                data_to_insert = (
                    customer['customer_id'],
                    customer['first_name'],
                    customer['last_name'],
                    customer['email'],
                    customer['phone'],
                    customer['address']
                )
                cursor.execute(insert_sql, data_to_insert)

        elif 'order' in file_name:
            insert_sql = """
                INSERT INTO myschema1.orders (order_id, order_date, total_amount, customer_id)
                VALUES (%s, %s, %s, %s)
                """
            for order in data:
                data_to_insert = (
                    order['order_id'],
                    order['order_date'],
                    order['total_amount'],
                    order['customer_id']
                )
                cursor.execute(insert_sql, data_to_insert)

        conn.commit()
    except Exception as e:
        print(f"Error during database operation: {e}")
        conn.rollback()

    finally:
        s3_client.delete_object(Bucket=S3_EVENT_DATA, Key=file_name)
        print(f"Object deleted from input bucket: {file_name}")

        cursor.close()
        conn.close()

        return {
            'statusCode': 200,
            'body': 'Data inserted to DB successfully!'
        }

