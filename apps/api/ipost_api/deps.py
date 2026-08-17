from fastapi import Depends, HTTPException

from ipost.settings import Settings, get_settings
from ipost.token_store import InstagramToken, load_token


def settings_dep() -> Settings:
    return get_settings()


def require_token(settings: Settings = Depends(settings_dep)) -> InstagramToken:
    token = load_token(settings)
    if token is None:
        raise HTTPException(status_code=401, detail="Instagram is not connected")
    return token
