from __future__ import annotations

import json
import os
from pathlib import Path

from ipost.settings import get_settings

os.environ["IPOST_MOCK_BEDROCK"] = "true"
get_settings.cache_clear()

from ipost.agents.lambda_handler import lambda_handler
from ipost.agents.pipeline import generate_job
from ipost.agents.schemas import TopicSpec, TrackSpec
from ipost.agents.templates import PLANNER_INSTRUCTIONS, apply_reel_hashtags
from ipost.agents.topic import eligible_topics, pick_audio, pick_topic
from ipost.brand import BrandKit, StyleRef, apply_brand, load_brand_kit, save_brand_kit


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_reel_caption_paragraphs() -> None:
    formatted = apply_reel_hashtags(
        "Às vezes, a esperança é a única luz que temos em meio à escuridão. "
        "Ela nos lembra que, mesmo quando tudo parece perdido, há um caminho à frente. "
        "Permita-se sentir essa luz e siga em frente, um passo de cada vez."
    )
    _assert(
        formatted
        == (
            "Às vezes, a esperança é a única luz que temos em meio à escuridão.\n\n"
            "Ela nos lembra que, mesmo quando tudo parece perdido, há um caminho à frente.\n\n"
            "Permita-se sentir essa luz e siga em frente, um passo de cada vez.\n\n"
            "#fé #deus #devocional #esperança #oração"
        ),
        formatted,
    )


def test_topic_rotation() -> None:
    topics = [
        TopicSpec(slug="faith", name="Faith", weight=35, enabled=True, audio_ids=["quiet"]),
        TopicSpec(slug="viral", name="Viral", weight=10, enabled=True, audio_ids=[]),
    ]
    tracks = [
        TrackSpec(id="quiet", title="Quiet", artist="Library", topics=["faith"], path="audio/quiet.mp3"),
    ]
    first = pick_topic(topics, job_type="STORY")
    _assert(first.enabled, "picked a disabled topic")
    _assert(first.slug == "faith", first.slug)
    viral = [item for item in eligible_topics(topics, job_type="REEL") if item.slug == "viral"]
    _assert(viral == [], "viral reels should require 5 tracks")
    audio = pick_audio(first, tracks)
    _assert(audio is not None and audio.id == "quiet", "tagged topic should resolve audio")
    print("topic rotation ok:", first.slug, audio.id)


def test_brand_kit_feeds_prompts() -> None:
    settings = get_settings()
    original = load_brand_kit(settings)
    try:
        kit = BrandKit(
            voice_tone="Speak like a late-night kitchen table.",
            banned=["No slogans"],
            refs=[
                StyleRef(
                    id="test-ref",
                    url="https://example.com/ref.jpg",
                    note="kitchen light",
                    topic="faith",
                )
            ],
        )
        save_brand_kit(kit, settings)
        loaded = load_brand_kit(settings)
        _assert(loaded.voice_tone == kit.voice_tone, loaded.voice_tone)
        _assert("No slogans" in loaded.banned_text(), loaded.banned_text())
        _assert(loaded.ref_lines(), "style refs missing")
        rendered = apply_brand(PLANNER_INSTRUCTIONS, loaded)
        _assert("late-night kitchen table" in rendered, rendered)
        _assert("No slogans" in rendered, rendered)
        print("brand kit ok:", loaded.ref_lines()[0])
    finally:
        save_brand_kit(original, settings)


def test_story_handler() -> None:
    result = lambda_handler({"action": "generate", "type": "STORY", "date": "2026-08-17"}, None)
    _assert(result["statusCode"] == 200, result.get("body", ""))
    body = json.loads(result["body"])
    job = body["job"]
    _assert(job["status"] == "APPROVED", job["status"])
    _assert(job["score"] >= 7.0, str(job["score"]))
    _assert(Path(job["still_path"]).is_file(), job["still_path"])
    _assert(job["type"] == "STORY", job["type"])
    print("story handler ok:", job["id"], job["score"])


def test_reel_generate() -> None:
    import asyncio

    from ipost.errors import ConfigError

    try:
        job = asyncio.run(generate_job("REEL", date="2026-08-17"))
    except ConfigError as exc:
        print("reel generate needs a tagged audio file:", exc)
        return
    _assert(job.status == "NEEDS_REVIEW", job.status)
    _assert(job.attempt == 3, str(job.attempt))
    _assert(Path(job.still_path).is_file(), job.still_path)
    _assert("#fé" in job.caption, job.caption)
    print("reel generate ok:", job.id, job.score, job.must_fix)


def main() -> None:
    settings = get_settings()
    _assert(settings.ipost_mock_bedrock, "test_simple requires IPOST_MOCK_BEDROCK=true")
    print("Testing iPost agents (mocked Bedrock)")
    print("=" * 60)
    test_reel_caption_paragraphs()
    test_topic_rotation()
    test_brand_kit_feeds_prompts()
    test_story_handler()
    test_reel_generate()
    print("=" * 60)
    print("test_simple passed")


if __name__ == "__main__":
    main()
