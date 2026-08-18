from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from ipost.agents.schemas import JobInsights, JobRecord, TopicSpec
from ipost.config_store import list_topics, upsert_topic
from ipost.instagram import (
    InstagramError,
    get_media,
    get_media_insights,
    token_has_insights,
)
from ipost.jobs import list_jobs, save_job
from ipost.settings import Settings
from ipost.token_store import InstagramToken

LOOKBACK_DAYS = 14
STORY_MAX_AGE_DAYS = 1
WEIGHT_MIN = 10
WEIGHT_MAX = 40
WEIGHT_CENTER = 20
TZ = ZoneInfo("America/Sao_Paulo")

REEL_METRIC_SETS = (
    "views,reach,saved,likes,comments,shares,total_interactions",
    "views,reach,saved,shares",
    "views,reach",
)
STORY_METRIC_SETS = (
    "views,reach,replies,shares,total_interactions",
    "views,reach,replies",
    "views,reach",
)


class InsightsError(RuntimeError):
    pass


def _today(day: str | None = None) -> str:
    return day or datetime.now(TZ).date().isoformat()


def _parse_day(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def _metric_int(raw: object) -> int:
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, dict):
        return int(sum(item for item in raw.values() if isinstance(item, (int, float))))
    return 0


def insights_from_graph(rows: list[dict], media: dict | None = None) -> JobInsights:
    values: dict[str, int] = {}
    aliases = {"plays": "views", "impressions": "views"}
    for row in rows:
        name = str(row.get("name") or "")
        field = aliases.get(name, name)
        entries = row.get("values") or []
        raw = entries[-1].get("value") if isinstance(entries, list) and entries else 0
        values[field] = _metric_int(raw)
    result = JobInsights(
        views=values.get("views", 0),
        reach=values.get("reach", 0),
        saved=values.get("saved", 0),
        likes=values.get("likes", 0),
        comments=values.get("comments", 0),
        shares=values.get("shares", 0),
        replies=values.get("replies", 0),
        total_interactions=values.get("total_interactions", 0),
    )
    if media:
        if not result.likes:
            result.likes = _metric_int(media.get("like_count"))
        if not result.comments:
            result.comments = _metric_int(media.get("comments_count"))
    return result


def reel_score(insights: JobInsights | None) -> float:
    if insights is None:
        return 0.0
    return float(insights.views or insights.reach or 0)


def should_fetch(job: JobRecord, today: str | None = None) -> bool:
    if job.status != "PUBLISHED" or not job.ig_media_id:
        return False
    day = _today(today)
    try:
        age = (_parse_day(day) - _parse_day(job.date)).days
    except ValueError:
        return False
    if age < 0:
        return False
    if job.type == "STORY":
        return age <= STORY_MAX_AGE_DAYS
    return age <= LOOKBACK_DAYS


def _in_window(job: JobRecord, today: str, days: int) -> bool:
    if job.status != "PUBLISHED" or job.type != "REEL" or job.insights is None:
        return False
    try:
        age = (_parse_day(today) - _parse_day(job.date)).days
    except ValueError:
        return False
    return 0 <= age <= days


def _topic_averages(jobs: list[JobRecord], today: str, days: int = LOOKBACK_DAYS) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for job in jobs:
        if not _in_window(job, today, days):
            continue
        score = reel_score(job.insights)
        if score <= 0:
            continue
        buckets.setdefault(job.topic, []).append(score)
    return {slug: sum(scores) / len(scores) for slug, scores in buckets.items() if scores}


def apply_topic_weights(
    topics: list[TopicSpec],
    jobs: list[JobRecord],
    today: str | None = None,
) -> list[TopicSpec]:
    day = _today(today)
    averages = _topic_averages(jobs, day)
    if not averages:
        return topics
    mean = sum(averages.values()) / len(averages)
    if mean <= 0:
        return topics
    updated: list[TopicSpec] = []
    for topic in topics:
        next_topic = topic.model_copy()
        if topic.slug in averages:
            ratio = averages[topic.slug] / mean
            next_topic.weight = int(max(WEIGHT_MIN, min(WEIGHT_MAX, round(WEIGHT_CENTER * ratio))))
        updated.append(next_topic)
    return updated


def track_play_scores(jobs: list[JobRecord], today: str | None = None) -> dict[str, float]:
    day = _today(today)
    buckets: dict[str, list[float]] = {}
    for job in jobs:
        if not job.audio_id or not _in_window(job, day, LOOKBACK_DAYS):
            continue
        score = reel_score(job.insights)
        if score <= 0:
            continue
        buckets.setdefault(job.audio_id, []).append(score)
    return {track_id: sum(scores) / len(scores) for track_id, scores in buckets.items() if scores}


def performance_note(jobs: list[JobRecord], today: str | None = None) -> str:
    averages = _topic_averages(jobs, _today(today))
    if not averages:
        return "(none yet)"
    best = max(averages, key=averages.get)
    label = best.replace("-", " ").capitalize()
    return f"{label} has been reaching more this week"


def _unavailable(exc: InstagramError) -> bool:
    text = str(exc).lower()
    payload = str(exc.payload).lower()
    blob = f"{text} {payload}"
    return any(
        needle in blob
        for needle in (
            "does not exist",
            "unsupported get request",
            "object with id",
            "expired",
            "(100)",
            "(803)",
        )
    )


def _permission_denied(exc: InstagramError) -> bool:
    blob = f"{exc} {exc.payload}".lower()
    return any(
        needle in blob
        for needle in ("permission", "oauthexception", "(190)", "missing permission", "not authorized")
    )


async def fetch_job_insights(
    job: JobRecord,
    settings: Settings,
    token: InstagramToken,
) -> JobRecord:
    if not job.ig_media_id:
        raise InsightsError("Job has no Instagram media id")
    media = await get_media(settings, token, job.ig_media_id)
    product = str(media.get("media_product_type") or job.type)
    sets = STORY_METRIC_SETS if product == "STORY" or job.type == "STORY" else REEL_METRIC_SETS
    last_error: InstagramError | None = None
    rows: list[dict] = []
    for metrics in sets:
        try:
            rows = await get_media_insights(settings, token, job.ig_media_id, metrics)
            last_error = None
            break
        except InstagramError as exc:
            last_error = exc
            if _permission_denied(exc):
                raise InsightsError("Reconnect Instagram to grant insights access.") from exc
            if _unavailable(exc):
                raise
    if last_error is not None:
        raise last_error
    job.insights = insights_from_graph(rows, media)
    job.insights_synced_at = datetime.now(TZ).isoformat(timespec="seconds")
    return job


async def refresh_job_insights(
    job: JobRecord,
    settings: Settings,
    token: InstagramToken,
) -> JobRecord:
    if not token_has_insights(token):
        raise InsightsError("Reconnect Instagram to grant insights access.")
    job = await fetch_job_insights(job, settings, token)
    save_job(job, settings)
    persist_topic_weights(list_jobs(settings), settings)
    return job


def persist_topic_weights(jobs: list[JobRecord], settings: Settings) -> list[TopicSpec]:
    current = list_topics(settings)
    updated = apply_topic_weights(current, jobs)
    for topic, next_topic in zip(current, updated, strict=True):
        if topic.weight != next_topic.weight:
            upsert_topic(next_topic, settings)
    return updated


async def sync_insights(settings: Settings, token: InstagramToken) -> dict:
    if not token_has_insights(token):
        raise InsightsError("Reconnect Instagram to grant insights access.")
    today = _today()
    synced = 0
    skipped = 0
    errors: list[str] = []
    for job in list_jobs(settings):
        if not should_fetch(job, today):
            continue
        try:
            await fetch_job_insights(job, settings, token)
            save_job(job, settings)
            synced += 1
        except InstagramError as exc:
            skipped += 1
            if _permission_denied(exc):
                raise InsightsError("Reconnect Instagram to grant insights access.") from exc
            if not _unavailable(exc):
                errors.append(f"{job.id}: {exc}")
        except InsightsError as exc:
            skipped += 1
            errors.append(f"{job.id}: {exc}")
    jobs = list_jobs(settings)
    weights = persist_topic_weights(jobs, settings)
    return {
        "synced": synced,
        "skipped": skipped,
        "errors": errors,
        "performance_note": performance_note(jobs, today),
        "weights": {topic.slug: topic.weight for topic in weights},
    }
