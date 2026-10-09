from __future__ import annotations

import os


class S3StorageAdapter:
    def __init__(
        self,
        bucket: str,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
        endpoint_url: str | None = None,
        public_url: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.access_key = access_key or os.environ.get("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.endpoint_url = endpoint_url
        self.public_url = public_url
        self._client = None

    async def connect(self) -> None:
        try:
            import aioboto3

            self._client = aioboto3.Session()
        except ImportError as exc:
            raise RuntimeError("aioboto3 is required. Install with: pip install aioboto3") from exc

    async def disconnect(self) -> None:
        self._client = None

    async def _get_client(self):
        if self._client is None:
            await self.connect()
        return self._client

    async def write(self, path: str, data: bytes, content_type: str | None = None) -> None:
        session = await self._get_client()
        async with session.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        ) as s3:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            await s3.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=data,
                **extra_args,
            )

    async def read(self, path: str) -> bytes:
        session = await self._get_client()
        async with session.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        ) as s3:
            response = await s3.get_object(Bucket=self.bucket, Key=path)
            return await response["Body"].read()

    async def delete(self, path: str) -> bool:
        session = await self._get_client()
        async with session.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        ) as s3:
            await s3.delete_object(Bucket=self.bucket, Key=path)
            return True

    async def exists(self, path: str) -> bool:
        """Check existence, propagating permission and backend failures."""
        from botocore.exceptions import ClientError

        session = await self._get_client()
        async with session.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        ) as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=path)
                return True
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code", ""))
                if code in {"404", "NoSuchKey", "NotFound"}:
                    return False
                raise

    async def size(self, path: str) -> int:
        session = await self._get_client()
        async with session.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        ) as s3:
            response = await s3.head_object(Bucket=self.bucket, Key=path)
            return response.get("ContentLength", 0)

    async def list(self, prefix: str = "") -> list[str]:
        session = await self._get_client()
        async with session.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        ) as s3:
            keys: list[str] = []
            request: dict[str, str] = {"Bucket": self.bucket, "Prefix": prefix}
            while True:
                response = await s3.list_objects_v2(**request)
                keys.extend(obj["Key"] for obj in response.get("Contents", []))
                if not response.get("IsTruncated"):
                    return keys
                token = response.get("NextContinuationToken")
                if not token:
                    return keys
                request["ContinuationToken"] = token

    def get_url(self, path: str) -> str:
        if self.public_url:
            return f"{self.public_url}/{path}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{path}"

    async def get_signed_url(self, path: str, expires_in: int = 900) -> str:
        """Return a short-lived presigned URL for private object storage."""
        session = await self._get_client()
        async with session.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        ) as s3:
            return await s3.generate_presigned_url(
                "get_object", Params={"Bucket": self.bucket, "Key": path}, ExpiresIn=max(1, expires_in)
            )
