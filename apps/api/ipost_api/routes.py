from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ipost.fixtures import write_placeholder_still, write_tone_wav
from ipost.instagram import (
    InstagramError,
    authorization_url,
    exchange_code,
    publish_reel,
    publish_story,
)
from ipost.mux import MuxError, mux_still_with_audio
from ipost.settings import Settings
from ipost.storage import StorageError, upload_bytes, upload_file
from ipost.token_store import days_until_expiry, load_token, save_token
from ipost_api.deps import require_token, settings_dep

router = APIRouter()


class PublishStoryBody(BaseModel):
    image_url: str


class PublishReelBody(BaseModel):
    video_url: str
    caption: str = "iPost phase 0"


@router.get("/auth/instagram")
def start_instagram_login(settings: Settings = Depends(settings_dep)) -> RedirectResponse:
    if not settings.instagram_app_id:
        raise HTTPException(status_code=500, detail="INSTAGRAM_APP_ID is missing")
    return RedirectResponse(authorization_url(settings))


@router.get("/auth/instagram/callback")
async def instagram_callback(
    code: str | None = None,
    error: str | None = None,
    settings: Settings = Depends(settings_dep),
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    try:
        token = await exchange_code(settings, code)
    except InstagramError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_token(settings, token)
    return RedirectResponse("/?connected=1")


@router.get("/auth/status")
def auth_status(settings: Settings = Depends(settings_dep)) -> dict:
    token = load_token(settings)
    if token is None:
        return {"connected": False}
    return {
        "connected": True,
        "user_id": token.user_id,
        "username": token.username,
        "days_until_expiry": days_until_expiry(token),
        "permissions": token.permissions,
    }


@router.post("/phase0/placeholder-story")
def placeholder_story(settings: Settings = Depends(settings_dep)) -> dict:
    still = write_placeholder_still(settings.token_file.parent / "phase0-story.jpg")
    try:
        url = upload_file(settings, "phase0/story.jpg", still, "image/jpeg")
    except StorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"image_url": url}


@router.post("/phase0/placeholder-reel")
def placeholder_reel(settings: Settings = Depends(settings_dep)) -> dict:
    work = settings.token_file.parent
    still = write_placeholder_still(work / "phase0-reel.jpg", "iPost Reel")
    audio = write_tone_wav(work / "phase0-tone.wav")
    video = work / "phase0-reel.mp4"
    try:
        mux_still_with_audio(still, audio, video)
        url = upload_file(settings, "phase0/reel.mp4", video, "video/mp4")
    except (MuxError, StorageError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"video_url": url}


@router.post("/phase0/upload")
async def upload_media(
    kind: str = Form(...),
    file: UploadFile = File(...),
    settings: Settings = Depends(settings_dep),
) -> dict:
    data = await file.read()
    if kind == "story":
        path = "phase0/upload-story.jpg"
        content_type = file.content_type or "image/jpeg"
        key = "image_url"
    elif kind == "reel":
        path = "phase0/upload-reel.mp4"
        content_type = file.content_type or "video/mp4"
        key = "video_url"
    else:
        raise HTTPException(status_code=400, detail="kind must be story or reel")
    try:
        url = upload_bytes(settings, path, data, content_type)
    except StorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {key: url}


@router.post("/phase0/publish-story")
async def publish_story_route(
    body: PublishStoryBody,
    settings: Settings = Depends(settings_dep),
    token=Depends(require_token),
) -> dict:
    try:
        media_id = await publish_story(settings, token, body.image_url)
    except InstagramError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "payload": exc.payload}) from exc
    return {"media_id": media_id, "type": "STORY"}


@router.post("/phase0/publish-reel")
async def publish_reel_route(
    body: PublishReelBody,
    settings: Settings = Depends(settings_dep),
    token=Depends(require_token),
) -> dict:
    try:
        media_id = await publish_reel(settings, token, body.video_url, body.caption)
    except InstagramError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "payload": exc.payload}) from exc
    return {"media_id": media_id, "type": "REEL"}
