from fastapi import Depends, HTTPException, Request

from ipost.auth import SESSION_COOKIE, get_user, read_session
from ipost.errors import ConfigError
from ipost.settings import Settings, get_settings
from ipost.token_store import InstagramToken, load_token


def settings_dep() -> Settings:
    return get_settings()


def require_token(settings: Settings = Depends(settings_dep)) -> InstagramToken:
    token = load_token(settings)
    if token is None:
        raise HTTPException(status_code=401, detail="Instagram is not connected")
    return token


def require_admin(request: Request, settings: Settings = Depends(settings_dep)) -> str:
    if not settings.session_secret:
        raise HTTPException(status_code=503, detail="SESSION_SECRET is missing")
    username = read_session(request.cookies.get(SESSION_COOKIE, ""), settings.session_secret)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user = get_user(username, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username
