def get_common_tags(env: str) -> dict:
    return {
        "Environment": env,
        "ManagedBy": "Pulumi",
        "Project": "MyProject",
        "Owner": "Joanna Kiesiak",
    }
