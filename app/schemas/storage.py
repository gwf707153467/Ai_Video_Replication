from pydantic import BaseModel


class BucketStatus(BaseModel):
    bucket_name: str
    exists: bool


class StorageBootstrapResponse(BaseModel):
    buckets: list[BucketStatus]
