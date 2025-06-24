# naming_utils.py


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
