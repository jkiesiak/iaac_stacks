import json
import logging
import os
from typing import Any

import boto3

s3 = boto3.client("s3", region_name="eu-west-2")


s3_bucket_name = os.environ.get("S3_BUCKET_NAME")
aws_profile = os.environ.get("AWS_PROFILE")



def lambda_backup_to_s3(s3_bucket_name_hardcoded: str):
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


def lambda_insert_into_database(event, context, file: Any):
    # TODO: refactor function
    logging.warning("TODO : Add body of function")

if __name__ == "__main__":

    s3_bucket_name_hardcoded = "bucket-v2-joanna-pipeline"

    lambda_backup_to_s3(s3_bucket_name_hardcoded)

    lambda_insert_into_database()

