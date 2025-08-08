# naming_utils.py
import random
import string
import pulumi
import pulumi_aws as aws
import pulumi_random as random
import subprocess
import os


def get_resource_name(resource_type: str, env: str) -> str:
    """
    Generates consistent resource names with environment prefix.

    Args:
        resource_type (str): The base resource type/name.
        env (str): Environment name (e.g., dev, prod).

    Returns:
        str: Combined resource name.
    """
    return f"{resource_type}-{env}"

def generate_password(length=16):
    chars = string.ascii_letters + string.digits + "!#$%&*-_=+[]{}<>:?"
    return ''.join(random.choice(chars) for _ in range(length))

# --- Apply schema after DB creation (Terraform null_resource equivalent)
def apply_schema(args):
    rds_address, pwd, _ = args
    command = [
        "psql",
        "--echo-queries",
        "-h", rds_address,
        "-U", "postgres",
        "-f", "sql_schema/schema.sql"
    ]
    env_vars = {
        **os.environ,
        "PGPASSWORD": pwd
    }
    print(f"Applying schema to RDS at {rds_address}...")
    subprocess.run(command, check=True, env=env_vars)
