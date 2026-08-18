from __future__ import annotations

from ipost.agents.schemas import TopicSlug, TopicSpec, TrackSpec
from ipost.seed import SEED_TOPICS, SEED_TRACKS


def eligible_topics(
    topics: list[TopicSpec] | None = None,
    *,
    min_audio_for_reel: int = 5,
    job_type: str = "STORY",
) -> list[TopicSpec]:
    if topics is None:
        from ipost.config_store import list_topics

        topics = list_topics()
    result: list[TopicSpec] = []
    for topic in topics:
        if not topic.enabled:
            continue
        if job_type == "REEL" and topic.slug == "viral" and len(topic.audio_ids) < min_audio_for_reel:
            continue
        result.append(topic)
    return result


def pick_topic(
    topics: list[TopicSpec] | None = None,
    *,
    job_type: str = "STORY",
    exclude_last: TopicSlug | None = None,
) -> TopicSpec:
    pool = eligible_topics(topics, job_type=job_type)
    if not pool:
        raise ValueError("No eligible topics")
    ranked = sorted(
        pool,
        key=lambda item: (
            0 if item.last_used is None else 1,
            item.last_used or "",
            -item.weight,
        ),
    )
    if exclude_last and len(ranked) > 1:
        ranked = [item for item in ranked if item.slug != exclude_last] or ranked
    return ranked[0]


def pick_audio(topic: TopicSpec, tracks: list[TrackSpec] | None = None) -> TrackSpec | None:
    if tracks is None:
        from ipost.config_store import list_tracks

        tracks = list_tracks()
    candidates = [track for track in tracks if track.id in topic.audio_ids]
    if not candidates:
        return None
    ranked = sorted(candidates, key=lambda item: (0 if item.last_used is None else 1, item.last_used or ""))
    return ranked[0]


TOPICS = SEED_TOPICS
TRACKS = SEED_TRACKS
