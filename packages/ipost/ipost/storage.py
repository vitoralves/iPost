from __future__ import annotations

from pathlib import Path

from supabase import Client, create_client

from ipost.settings import Settings


class StorageError(RuntimeError):
    pass


def supabase_client(settings: Settings) -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise StorageError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _bucket_name(bucket: object) -> str | None:
    if isinstance(bucket, dict):
        return bucket.get("name")
    return getattr(bucket, "name", None)


def _ensure_bucket(settings: Settings, name: str, *, public: bool) -> None:
    client = supabase_client(settings)
    buckets = client.storage.list_buckets()
    names = {_bucket_name(bucket) for bucket in buckets}
    if name in names:
        return
    client.storage.create_bucket(
        name,
        options={"public": public, "file_size_limit": "52428800"},
    )


def ensure_outbox_bucket(settings: Settings) -> None:
    _ensure_bucket(settings, settings.supabase_outbox_bucket, public=True)


def ensure_private_bucket(settings: Settings) -> None:
    _ensure_bucket(settings, settings.supabase_private_bucket, public=False)


def upload_private_bytes(settings: Settings, object_path: str, data: bytes, content_type: str) -> str:
    ensure_private_bucket(settings)
    client = supabase_client(settings)
    bucket = client.storage.from_(settings.supabase_private_bucket)
    bucket.upload(
        object_path,
        data,
        file_options={
            "content-type": content_type,
            "upsert": "true",
        },
    )
    return object_path


def delete_private_object(settings: Settings, object_path: str) -> None:
    ensure_private_bucket(settings)
    client = supabase_client(settings)
    client.storage.from_(settings.supabase_private_bucket).remove([object_path])


def signed_private_url(settings: Settings, object_path: str, expires_in: int = 3600) -> str:
    ensure_private_bucket(settings)
    client = supabase_client(settings)
    payload = client.storage.from_(settings.supabase_private_bucket).create_signed_url(
        object_path, expires_in
    )
    url = (
        payload.get("signedURL")
        or payload.get("signedUrl")
        or payload.get("signed_url")
    )
    if not url:
        raise StorageError("Could not sign private object")
    return url


def download_private_bytes(settings: Settings, object_path: str) -> bytes | None:
    ensure_private_bucket(settings)
    client = supabase_client(settings)
    try:
        return client.storage.from_(settings.supabase_private_bucket).download(object_path)
    except Exception:
        return None


def public_object_url(settings: Settings, object_path: str) -> str:
    base = settings.supabase_url.rstrip("/")
    return (
        f"{base}/storage/v1/object/public/"
        f"{settings.supabase_outbox_bucket}/{object_path.lstrip('/')}"
    )


def upload_bytes(
    settings: Settings,
    object_path: str,
    data: bytes,
    content_type: str,
) -> str:
    ensure_outbox_bucket(settings)
    client = supabase_client(settings)
    bucket = client.storage.from_(settings.supabase_outbox_bucket)
    bucket.upload(
        object_path,
        data,
        file_options={
            "content-type": content_type,
            "upsert": "true",
        },
    )
    return public_object_url(settings, object_path)


def upload_file(settings: Settings, object_path: str, file_path: Path, content_type: str) -> str:
    return upload_bytes(settings, object_path, file_path.read_bytes(), content_type)
