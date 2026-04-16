from uuid import uuid4


def generate_public_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def generate_claim_token() -> str:
    return generate_public_id("clm")
