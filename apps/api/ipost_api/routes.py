from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse, Response
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
from ipost.agents.pipeline import generate_job
from ipost.agents.schemas import JobRecord, JobType, TopicSlug, TopicSpec, TrackSpec
from ipost.brand import BrandKit, StyleRef, load_brand_kit, save_brand_kit
from ipost.config_store import (
    delete_brand_ref,
    get_brand_ref,
    list_topics,
    list_tracks,
    upsert_brand_ref,
    upsert_topic,
    upsert_track,
)
from ipost.errors import ConfigError
from ipost.job_actions import (
    JobActionError,
    finalize_generated_job,
    publish_story_job,
    set_terminal_status,
)
from ipost.jobs import get_job, list_jobs, save_job
from ipost.settings import Settings
from ipost.storage import StorageError, download_private_bytes, upload_bytes, upload_file, upload_private_bytes
from ipost.token_store import days_until_expiry, load_token, save_token
from ipost_api.deps import require_token, settings_dep

router = APIRouter()


class PublishStoryBody(BaseModel):
    image_url: str


class PublishReelBody(BaseModel):
    video_url: str
    caption: str = "iPost phase 0"


class GenerateBody(BaseModel):
    type: JobType = "STORY"
    date: str | None = None
    topic: TopicSlug | None = None


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


@router.post("/jobs/generate")
async def generate_route(body: GenerateBody, settings: Settings = Depends(settings_dep)) -> dict:
    if body.type != "STORY":
        raise HTTPException(status_code=400, detail="Only Story generate is available in Phase 1")
    job = await generate_job(body.type, settings=settings, date=body.date, forced_topic=body.topic)
    try:
        job = finalize_generated_job(job, settings)
    except (ConfigError, JobActionError) as exc:
        try:
            save_job(job, settings)
        except ConfigError:
            pass
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
        job, media_id = await publish_story_job(job, settings, token)
    except JobActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**job.model_dump(), "media_id": media_id}


@router.post("/jobs/{job_id}/reject")
def reject_job_route(job_id: str, settings: Settings = Depends(settings_dep)) -> dict:
    return _set_terminal(job_id, "REJECTED", settings)


@router.post("/jobs/{job_id}/skip")
def skip_job_route(job_id: str, settings: Settings = Depends(settings_dep)) -> dict:
    return _set_terminal(job_id, "SKIPPED", settings)


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


@router.post("/brand-kit/refs")
async def upload_brand_ref(
    file: UploadFile = File(...),
    ref_id: str | None = Form(default=None),
    note: str = Form(default=""),
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
    path = f"brand/refs/{ident}{suffix}"
    try:
        upload_private_bytes(settings, path, data, content_type)
        ref = upsert_brand_ref(StyleRef(id=ident, path=path, note=note.strip()), settings)
    except (ConfigError, StorageError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ref.model_dump()


@router.get("/brand-kit/refs/{ref_id}")
def get_brand_ref_file(ref_id: str, settings: Settings = Depends(settings_dep)) -> Response:
    try:
        ref = get_brand_ref(ref_id, settings)
    except ConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if ref is None or not ref.path:
        raise HTTPException(status_code=404, detail="Style ref not found")
    data = download_private_bytes(settings, ref.path)
    if not data:
        raise HTTPException(status_code=404, detail="Style ref file is missing")
    media = "image/jpeg"
    if ref.path.endswith(".png"):
        media = "image/png"
    elif ref.path.endswith(".webp"):
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
