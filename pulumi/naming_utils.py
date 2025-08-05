# naming_utils.py
import random
import string


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
