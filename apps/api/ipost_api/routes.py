from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from uuid import uuid4

from ipost.instagram import (
    INSIGHTS_SCOPE,
    InstagramError,
    authorization_url,
    exchange_code,
)
from ipost.agents.canvas import StillError
from ipost.agents.pipeline import generate_job
from ipost.agents.schemas import JobRecord, JobType, TopicSlug, TopicSpec, TrackSpec
from ipost.auth import SESSION_COOKIE, authenticate, cookie_params, sign_session
from ipost.brand import BrandKit, StyleRef, load_brand_kit, save_brand_kit
from ipost.config_store import (
    delete_brand_ref,
    delete_track,
    get_brand_ref,
    get_track,
    list_topics,
    list_tracks,
    load_brand_ref_file,
    upsert_brand_ref,
    upsert_topic,
    upsert_track,
)
from ipost.errors import ConfigError
from ipost.insights import InsightsError, refresh_job_insights, sync_insights
from ipost.job_actions import (
    JobActionError,
    attach_reel_audio,
    finalize_generated_job,
    persist_incomplete_generate,
    publish_media_job,
    set_terminal_status,
)
from ipost.jobs import get_job, list_jobs, save_job
from ipost.notify import notify_generate_failed, notify_needs_review
from ipost.settings import Settings
from ipost.storage import StorageError, download_private_bytes, upload_private_bytes
from ipost.token_store import days_until_expiry, load_token, save_token
from ipost_api.deps import require_admin, require_token, settings_dep

public_router = APIRouter()
router = APIRouter()


class LoginBody(BaseModel):
    username: str
    password: str


class GenerateBody(BaseModel):
    type: JobType = "STORY"
    date: str | None = None
    topic: TopicSlug | None = None


class AttachAudioBody(BaseModel):
    track_id: str


@router.get("/auth/instagram")
def start_instagram_login(settings: Settings = Depends(settings_dep)) -> RedirectResponse:
    if not settings.instagram_app_id:
        raise HTTPException(status_code=500, detail="INSTAGRAM_APP_ID is missing")
    return RedirectResponse(authorization_url(settings))


@public_router.post("/auth/login")
def login(body: LoginBody, settings: Settings = Depends(settings_dep)) -> JSONResponse:
    if not settings.session_secret:
        raise HTTPException(status_code=503, detail="SESSION_SECRET is missing")
    try:
        username = authenticate(body.username, body.password, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    response = JSONResponse({"username": username})
    response.set_cookie(value=sign_session(username, settings.session_secret), **cookie_params(settings))
    return response


@public_router.post("/auth/logout")
def logout(settings: Settings = Depends(settings_dep)) -> JSONResponse:
    response = JSONResponse({"ok": True})
    params = cookie_params(settings)
    response.delete_cookie(
        SESSION_COOKIE,
        path=params["path"],
        secure=params["secure"],
        httponly=True,
        samesite=params["samesite"],
    )
    return response


@router.get("/auth/me")
def auth_me(username: str = Depends(require_admin)) -> dict:
    return {"username": username}


@public_router.get("/auth/instagram/callback")
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
        "has_insights": INSIGHTS_SCOPE in token.permissions,
    }


@router.post("/jobs/generate")
async def generate_route(body: GenerateBody, settings: Settings = Depends(settings_dep)) -> dict:
    job = None
    try:
        job = await generate_job(body.type, settings=settings, date=body.date, forced_topic=body.topic)
        job = finalize_generated_job(job, settings)
    except StillError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ConfigError, JobActionError) as exc:
        if job is not None:
            try:
                persist_incomplete_generate(job, settings, str(exc))
            except ConfigError:
                pass
            notify_generate_failed(job, settings, str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if job.status == "NEEDS_REVIEW":
        notify_needs_review(job, settings)
    return job.model_dump()


@router.get("/jobs")
def list_jobs_route(settings: Settings = Depends(settings_dep)) -> dict:
    try:
        return {"jobs": [item.model_dump() for item in list_jobs(settings)]}
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/jobs/{job_id}")
def get_job_route(job_id: str, settings: Settings = Depends(settings_dep)) -> dict:
    try:
        job = get_job(job_id, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()


@router.put("/jobs/{job_id}")
def put_job_route(job_id: str, body: JobRecord, settings: Settings = Depends(settings_dep)) -> dict:
    body.id = job_id
    try:
        return save_job(body, settings).model_dump()
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/publish")
async def publish_job_route(
    job_id: str,
    settings: Settings = Depends(settings_dep),
    token=Depends(require_token),
) -> dict:
    try:
        job = get_job(job_id, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        job, media_id = await publish_media_job(job, settings, token)
    except JobActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**job.model_dump(), "media_id": media_id}


@router.post("/jobs/{job_id}/insights")
async def refresh_job_insights_route(
    job_id: str,
    settings: Settings = Depends(settings_dep),
    token=Depends(require_token),
) -> dict:
    try:
        job = get_job(job_id, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "PUBLISHED":
        raise HTTPException(status_code=400, detail="Insights are available after publish")
    try:
        return (await refresh_job_insights(job, settings, token)).model_dump()
    except InsightsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InstagramError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/insights/sync")
async def sync_insights_route(
    settings: Settings = Depends(settings_dep),
    token=Depends(require_token),
) -> dict:
    try:
        return await sync_insights(settings, token)
    except InsightsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InstagramError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/reject")
def reject_job_route(job_id: str, settings: Settings = Depends(settings_dep)) -> dict:
    return _set_terminal(job_id, "REJECTED", settings)


@router.post("/jobs/{job_id}/skip")
def skip_job_route(job_id: str, settings: Settings = Depends(settings_dep)) -> dict:
    return _set_terminal(job_id, "SKIPPED", settings)


@router.post("/jobs/{job_id}/audio")
def attach_audio_route(
    job_id: str,
    body: AttachAudioBody,
    settings: Settings = Depends(settings_dep),
) -> dict:
    try:
        job = get_job(job_id, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return attach_reel_audio(job, body.track_id.strip(), settings).model_dump()
    except (ConfigError, JobActionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _set_terminal(job_id: str, status: str, settings: Settings) -> dict:
    try:
        job = get_job(job_id, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return set_terminal_status(job, status, settings).model_dump()
    except (ConfigError, JobActionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/brand-kit")
def get_brand_kit(settings: Settings = Depends(settings_dep)) -> dict:
    try:
        return load_brand_kit(settings).model_dump()
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/brand-kit")
def put_brand_kit(body: BrandKit, settings: Settings = Depends(settings_dep)) -> dict:
    try:
        return save_brand_kit(body, settings).model_dump()
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


_REF_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

_AUDIO_TYPES = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
}

_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".mp4"}

_AUDIO_MEDIA = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".mp4": "audio/mp4",
}


def _slug_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value.strip())
    return cleaned.strip("-_")[:40]


def _audio_suffix(filename: str | None, content_type: str) -> str | None:
    suffix = _AUDIO_TYPES.get(content_type)
    if suffix:
        return suffix
    name = (filename or "").rsplit(".", 1)
    if len(name) == 2:
        ext = f".{name[1].lower()}"
        if ext in _AUDIO_SUFFIXES:
            return ext
    return None


@router.post("/brand-kit/refs")
async def upload_brand_ref(
    file: UploadFile = File(...),
    ref_id: str | None = Form(default=None),
    note: str = Form(default=""),
    topic: str = Form(default=""),
    settings: Settings = Depends(settings_dep),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be 8MB or smaller")
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    suffix = _REF_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(status_code=400, detail="Use a JPEG, PNG, or WebP image")
    ident = (ref_id or "").strip() or file.filename or "ref"
    ident = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in ident)[:40]
    if not topic.strip():
        raise HTTPException(status_code=400, detail="Pick a topic for this style ref")
    path = f"brand/refs/{ident}{suffix}"
    try:
        upload_private_bytes(settings, path, data, content_type)
        ref = upsert_brand_ref(
            StyleRef(id=ident, path=path, note=note.strip(), topic=topic.strip()),
            settings,
        )
    except (ConfigError, StorageError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ref.model_dump()


@router.get("/brand-kit/refs/{ref_id}")
def get_brand_ref_file(ref_id: str, settings: Settings = Depends(settings_dep)) -> Response:
    try:
        loaded = load_brand_ref_file(ref_id, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if loaded is None:
        raise HTTPException(status_code=404, detail="Style ref not found")
    data, path = loaded
    media = "image/jpeg"
    if path.endswith(".png"):
        media = "image/png"
    elif path.endswith(".webp"):
        media = "image/webp"
    return Response(content=data, media_type=media)


@router.delete("/brand-kit/refs/{ref_id}")
def delete_brand_ref_route(ref_id: str, settings: Settings = Depends(settings_dep)) -> dict:
    try:
        delete_brand_ref(ref_id, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/topics")
def get_topics(settings: Settings = Depends(settings_dep)) -> dict:
    try:
        return {"topics": [item.model_dump() for item in list_topics(settings)]}
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/topics/{slug}")
def put_topic(slug: str, body: TopicSpec, settings: Settings = Depends(settings_dep)) -> dict:
    body.slug = slug
    try:
        return upsert_topic(body, settings).model_dump()
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/tracks")
def get_tracks(settings: Settings = Depends(settings_dep)) -> dict:
    try:
        return {"tracks": [item.model_dump() for item in list_tracks(settings)]}
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/tracks/{track_id}")
def put_track(track_id: str, body: TrackSpec, settings: Settings = Depends(settings_dep)) -> dict:
    body.id = track_id
    try:
        return upsert_track(body, settings).model_dump()
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/tracks/{track_id}")
def delete_track_route(track_id: str, settings: Settings = Depends(settings_dep)) -> dict:
    try:
        if get_track(track_id, settings) is None:
            raise HTTPException(status_code=404, detail="Track not found")
        delete_track(track_id, settings)
    except HTTPException:
        raise
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/tracks")
async def upload_track_route(
    file: UploadFile = File(...),
    track_id: str | None = Form(default=None),
    title: str = Form(default=""),
    artist: str = Form(default=""),
    topics: str = Form(default=""),
    settings: Settings = Depends(settings_dep),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 40 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio must be 40MB or smaller")
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    suffix = _audio_suffix(file.filename, content_type)
    if suffix is None:
        raise HTTPException(status_code=400, detail="Use an MP3, WAV, M4A, AAC, OGG, or FLAC file")
    ident = _slug_id(track_id or "")
    stem = (file.filename or "track").rsplit(".", 1)[0]
    try:
        existing = get_track(ident, settings) if ident else None
        if ident and existing is None:
            raise HTTPException(status_code=404, detail="Track not found")
        if existing is None:
            ident = _slug_id(title or stem) or "track"
            ident = f"{ident}-{uuid4().hex[:8]}"
            existing = TrackSpec(
                id=ident,
                title=(title.strip() or stem.replace("-", " ").replace("_", " ")).strip() or "Untitled",
                artist=(artist.strip() or "Library"),
                topics=[item.strip() for item in topics.split(",") if item.strip()],
            )
        path = f"audio/{existing.id}{suffix}"
        upload_private_bytes(settings, path, data, _AUDIO_MEDIA.get(suffix, "application/octet-stream"))
        existing.path = path
        if title.strip():
            existing.title = title.strip()
        if artist.strip():
            existing.artist = artist.strip()
        if topics.strip():
            existing.topics = [item.strip() for item in topics.split(",") if item.strip()]
        return upsert_track(existing, settings).model_dump()
    except HTTPException:
        raise
    except (ConfigError, StorageError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/tracks/{track_id}/file")
def get_track_file(track_id: str, settings: Settings = Depends(settings_dep)) -> Response:
    try:
        track = get_track(track_id, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if track is None or not track.path:
        raise HTTPException(status_code=404, detail="Track file not found")
    data = download_private_bytes(settings, track.path)
    if not data:
        raise HTTPException(status_code=404, detail="Track file is missing")
    name = track.path.rsplit(".", 1)
    ext = f".{name[1].lower()}" if len(name) == 2 else ".mp3"
    return Response(content=data, media_type=_AUDIO_MEDIA.get(ext, "application/octet-stream"))
