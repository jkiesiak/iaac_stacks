import json
import os
from typing import Any
import pandas as pd
from io import StringIO
import psycopg2
import boto3
import csv
import pymysql


s3_bucket_name = os.environ.get("S3_BUCKET_NAME")
aws_profile = os.environ.get("AWS_PROFILE")
rds_host = os.environ.get("HOST")
db_name = os.environ.get("your-database-name")
user_name = os.environ.get("your-username")
password = os.environ.get("your-password")

def lambda_function(event, context, s3_bucket_name_hardcoded: str):
    s3 = boto3.client("s3", region_name="eu-west-2")
    file_name = "customers.json"
    if os.path.getsize(file_name) == 0:
        print("File is empty!")
        return {
            "statusCode": 400,
            "body": "JSON file is empty"
        }

    with open(file_name, "rb") as local_file:
        json_string = local_file.read()
        try:
            json_data = json.loads(json_string)
        except json.JSONDecodeError as e:
            return {
            "statusCode": 400,
            "body": f"Invalid JSON: {str(e)}"
            }

    s3.put_object(
        Bucket=s3_bucket_name_hardcoded,
        Key=file_name,
        Body=json_string
    )

    return {
        "statusCode": 200,
        "body": json.dumps("Data inserted into s3"),
    }

 # Specify your RDS connection details
    rds_host = "your-rds-hostname"
    db_name = "your-database-name"
    user_name = "your-username"
    password = "your-password"

    # Specify your S3 bucket and file key
    s3_bucket = "your-s3-bucket"
    file_key = "path/to/your/file.csv"

    # Initialize RDS connection
    conn = psycopg2.connect(
        host=rds_host,
        port=port,
        database=db_name,
        user=user_name,
        password=password
    )

    # Initialize S3 and download the file
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=s3_bucket, Key=file_key)
    file_content = obj['Body'].read().decode('utf-8')

    # Parse CSV content using pandas
    df = pd.read_csv(StringIO(file_content))

    # Insert data into PostgreSQL table
    cursor = conn.cursor()
    # for index, row in df.iterrows():
    #     cursor.execute("INSERT INTO myschema1.customers (    customer_id, first_name, last_name, email, phone, address) VALUES (%s, %s, ...)",
    #                    (row['column1'], row['column2'], ...))
    #
    # # Commit changes and close the connection
    # conn.commit()
    # conn.close()

    return {
        'statusCode': 200,
        'body': 'File successfully loaded into PostgreSQL table.'
    }


if __name__ == "__main__":

    s3_bucket_name_hardcoded = "bucket-application-joa-test1"
    lambda_function(s3_bucket_name_hardcoded = s3_bucket_name_hardcoded)

