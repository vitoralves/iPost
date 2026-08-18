from __future__ import annotations

from ipost.agents.schemas import TopicSlug, TopicSpec, TrackSpec
from ipost.errors import ConfigError


def eligible_topics(
    topics: list[TopicSpec] | None = None,
    *,
    job_type: str = "STORY",
) -> list[TopicSpec]:
    if topics is None:
        from ipost.config_store import list_topics

        topics = list_topics()
    return [topic for topic in topics if topic.enabled]


def pick_topic(
    topics: list[TopicSpec] | None = None,
    *,
    job_type: str = "STORY",
    exclude_last: TopicSlug | None = None,
) -> TopicSpec:
    pool = eligible_topics(topics)
    if not pool:
        raise ConfigError("Add an enabled topic before generating.")
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


def pick_audio(
    topic: TopicSpec,
    tracks: list[TrackSpec] | None = None,
    plays: dict[str, float] | None = None,
) -> TrackSpec | None:
    if tracks is None:
        from ipost.config_store import list_tracks

        tracks = list_tracks()
    candidates = [
        track
        for track in tracks
        if (track.id in topic.audio_ids or topic.slug in track.topics) and track.path
    ]
    if not candidates:
        return None
    scores = plays or {}
    ranked = sorted(
        candidates,
        key=lambda item: (
            0 if item.last_used is None else 1,
            item.last_used or "",
            -scores.get(item.id, 0.0),
        ),
    )
    return ranked[0]
