from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from ipost.settings import Settings


class InstagramToken(BaseModel):
    access_token: str
    user_id: str
    username: str | None = None
    expires_at: datetime | None = None
    permissions: list[str] = Field(default_factory=list)


TOKEN_OBJECT = "instagram_token.json"


def load_token(settings: Settings) -> InstagramToken | None:
    if settings.supabase_url and settings.supabase_service_role_key:
        from ipost.storage import download_private_bytes

        raw = download_private_bytes(settings, TOKEN_OBJECT)
        if raw:
            return InstagramToken.model_validate_json(raw)

    path = settings.token_file
    if not path.exists():
        return None
    return InstagramToken.model_validate_json(path.read_text())


def save_token(settings: Settings, token: InstagramToken) -> None:
    payload = token.model_dump_json(indent=2)
    path = settings.token_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload)
    if settings.supabase_url and settings.supabase_service_role_key:
        from ipost.storage import upload_private_bytes

        upload_private_bytes(settings, TOKEN_OBJECT, payload.encode("utf-8"), "application/json")


def token_from_exchange(
    *,
    access_token: str,
    user_id: str,
    expires_in: int | None,
    username: str | None = None,
    permissions: list[str] | None = None,
) -> InstagramToken:
    expires_at = None
    if expires_in:
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    return InstagramToken(
        access_token=access_token,
        user_id=str(user_id),
        username=username,
        expires_at=expires_at,
        permissions=permissions or [],
    )


def days_until_expiry(token: InstagramToken) -> int | None:
    if token.expires_at is None:
        return None
    delta = token.expires_at - datetime.now(UTC)
    return max(0, delta.days)
