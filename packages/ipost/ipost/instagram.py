from urllib.parse import urlencode

import httpx

from ipost.settings import Settings
from ipost.token_store import InstagramToken, token_from_exchange

INSIGHTS_SCOPE = "instagram_business_manage_insights"

AUTH_SCOPES = (
    "instagram_business_basic",
    "instagram_business_content_publish",
    INSIGHTS_SCOPE,
)


class InstagramError(RuntimeError):
    def __init__(self, message: str, payload: dict | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


def _graph_error(payload: dict) -> dict | None:
    error = payload.get("error")
    if isinstance(error, dict):
        return error
    if error:
        return {"message": str(error)}
    return None


def _raise_for_graph(payload: dict) -> None:
    error = _graph_error(payload)
    if error:
        message = error.get("message") or "Instagram API error"
        code = error.get("code")
        if code is not None:
            message = f"{message} ({code})"
        raise InstagramError(message, payload)


def authorization_url(settings: Settings, state: str = "ipost") -> str:
    query = urlencode(
        {
            "client_id": settings.instagram_app_id,
            "redirect_uri": settings.instagram_redirect_uri,
            "response_type": "code",
            "scope": ",".join(AUTH_SCOPES),
            "state": state,
        }
    )
    return f"https://www.instagram.com/oauth/authorize?{query}"


def _parse_permissions(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str) and raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return []


async def exchange_code(settings: Settings, code: str) -> InstagramToken:
    async with httpx.AsyncClient(timeout=30) as client:
        short = await client.post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": settings.instagram_app_id,
                "client_secret": settings.instagram_app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": settings.instagram_redirect_uri,
                "code": code.removesuffix("#_"),
            },
        )
        short_payload = short.json()
        if short.status_code >= 400:
            raise InstagramError("Failed to exchange authorization code", short_payload)
        data = short_payload.get("data")
        if isinstance(data, list) and data:
            short_payload = data[0]
        short_token = short_payload.get("access_token")
        user_id = short_payload.get("user_id")
        if not short_token or not user_id:
            raise InstagramError("Token exchange missing access_token or user_id", short_payload)

        long_response = await client.get(
            "https://graph.instagram.com/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": settings.instagram_app_secret,
                "access_token": short_token,
            },
        )
        long_payload = long_response.json()
        if long_response.status_code >= 400:
            raise InstagramError("Failed to exchange long-lived token", long_payload)
        access_token = long_payload.get("access_token") or short_token
        expires_in = long_payload.get("expires_in")

        me = await client.get(
            f"{settings.instagram_graph_base}/me",
            params={"fields": "user_id,username", "access_token": access_token},
        )
        me_payload = me.json()
        username = me_payload.get("username") if me.status_code < 400 else None
        resolved_user_id = me_payload.get("user_id") or me_payload.get("id") or user_id

    return token_from_exchange(
        access_token=access_token,
        user_id=str(resolved_user_id),
        expires_in=int(expires_in) if expires_in else None,
        username=username,
        permissions=_parse_permissions(short_payload.get("permissions")),
    )


async def refresh_long_lived_token(settings: Settings, token: InstagramToken) -> InstagramToken:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://graph.instagram.com/refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": token.access_token,
            },
        )
        payload = response.json()
        if response.status_code >= 400:
            raise InstagramError("Failed to refresh Instagram token", payload)
        access_token = payload.get("access_token")
        if not access_token:
            raise InstagramError("Refresh response missing access_token", payload)
        return token_from_exchange(
            access_token=access_token,
            user_id=token.user_id,
            expires_in=payload.get("expires_in"),
            username=token.username,
            permissions=token.permissions,
        )


async def _create_container(
    settings: Settings,
    token: InstagramToken,
    params: dict[str, str],
) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.instagram_graph_base}/{token.user_id}/media",
            params={"access_token": token.access_token},
            data=params,
        )
        payload = response.json()
        _raise_for_graph(payload)
        if response.status_code >= 400:
            raise InstagramError("Failed to create media container", payload)
        container_id = payload.get("id")
        if not container_id:
            raise InstagramError("Container response missing id", payload)
        return str(container_id)


async def _wait_until_finished(
    settings: Settings,
    token: InstagramToken,
    container_id: str,
    *,
    attempts: int = 60,
    delay_seconds: float = 3,
) -> None:
    import asyncio

    async with httpx.AsyncClient(timeout=30) as client:
        for _ in range(attempts):
            response = await client.get(
                f"{settings.instagram_graph_base}/{container_id}",
                params={"fields": "status_code,status", "access_token": token.access_token},
            )
            payload = response.json()
            error = _graph_error(payload)
            if error and error.get("code") == 803:
                await asyncio.sleep(delay_seconds)
                continue
            _raise_for_graph(payload)
            status = payload.get("status_code")
            if status == "FINISHED":
                return
            if status in {"ERROR", "EXPIRED"}:
                raise InstagramError(f"Container {status}", payload)
            await asyncio.sleep(delay_seconds)
    raise InstagramError("Timed out waiting for media container", {"container_id": container_id})


async def _publish_container(
    settings: Settings,
    token: InstagramToken,
    container_id: str,
) -> str:
    import asyncio

    async with httpx.AsyncClient(timeout=60) as client:
        payload: dict = {}
        for attempt in range(4):
            response = await client.post(
                f"{settings.instagram_graph_base}/{token.user_id}/media_publish",
                params={"creation_id": container_id, "access_token": token.access_token},
            )
            payload = response.json()
            error = _graph_error(payload)
            if error and error.get("code") == 803 and attempt < 3:
                await asyncio.sleep(2)
                continue
            _raise_for_graph(payload)
            if response.status_code >= 400:
                raise InstagramError("Failed to publish media", payload)
            media_id = payload.get("id")
            if not media_id:
                raise InstagramError("Publish response missing id", payload)
            return str(media_id)
        raise InstagramError("Failed to publish media", payload)


async def publish_story(settings: Settings, token: InstagramToken, image_url: str) -> str:
    container_id = await _create_container(
        settings,
        token,
        {"image_url": image_url, "media_type": "STORIES"},
    )
    await _wait_until_finished(settings, token, container_id, attempts=20, delay_seconds=2)
    return await _publish_container(settings, token, container_id)


def token_has_insights(token: InstagramToken) -> bool:
    if not token.permissions:
        return True
    return INSIGHTS_SCOPE in token.permissions


async def get_media(settings: Settings, token: InstagramToken, media_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{settings.instagram_graph_base}/{media_id}",
            params={
                "fields": "id,media_type,media_product_type,like_count,comments_count",
                "access_token": token.access_token,
            },
        )
        payload = response.json()
        _raise_for_graph(payload)
        if response.status_code >= 400:
            raise InstagramError("Failed to load Instagram media", payload)
        return payload if isinstance(payload, dict) else {}


async def get_media_insights(
    settings: Settings,
    token: InstagramToken,
    media_id: str,
    metrics: str,
) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{settings.instagram_graph_base}/{media_id}/insights",
            params={"metric": metrics, "access_token": token.access_token},
        )
        payload = response.json()
        _raise_for_graph(payload)
        if response.status_code >= 400:
            raise InstagramError("Failed to load Instagram insights", payload)
        data = payload.get("data")
        return data if isinstance(data, list) else []


async def publish_reel(
    settings: Settings,
    token: InstagramToken,
    video_url: str,
    caption: str = "",
) -> str:
    params = {"video_url": video_url, "media_type": "REELS"}
    if caption:
        params["caption"] = caption
    container_id = await _create_container(settings, token, params)
    await _wait_until_finished(settings, token, container_id)
    return await _publish_container(settings, token, container_id)
