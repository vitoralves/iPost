from __future__ import annotations

from ipost.agents.schemas import TopicSpec, TrackSpec
from ipost.agents.templates import BANNED_TOPICS, VOICE_TONE
from ipost.brand import BrandKit, StyleRef

SEED_TOPICS: list[TopicSpec] = [
    TopicSpec(
        slug="faith",
        name="Faith",
        weight=35,
        enabled=True,
        last_used=None,
        audio_ids=["quiet-morning", "walking-in-light"],
        refs=["/media/mountains.jpg", "/media/valley.jpg", "/media/forest.jpg"],
    ),
    TopicSpec(
        slug="hope",
        name="Hope",
        weight=30,
        enabled=True,
        last_used=None,
        audio_ids=["quiet-morning", "new-season", "rise-again"],
        refs=["/media/water.jpg", "/media/hills.jpg", "/media/mist.jpg"],
    ),
    TopicSpec(
        slug="motivational",
        name="Motivational",
        weight=25,
        enabled=True,
        last_used=None,
        audio_ids=["walking-in-light", "rise-again", "push-through"],
        refs=["/media/boats.jpg", "/media/hills.jpg", "/media/mountains.jpg"],
    ),
    TopicSpec(
        slug="viral",
        name="Viral",
        weight=10,
        enabled=False,
        last_used=None,
        audio_ids=[],
        refs=["/media/mist.jpg", "/media/forest.jpg"],
    ),
]

SEED_TRACKS: list[TrackSpec] = [
    TrackSpec(
        id="quiet-morning",
        title="Quiet Morning",
        artist="Emahoy Tsegué-Maryam Guèbrou",
        duration="3:42",
        last_used=None,
        topics=["faith", "hope"],
    ),
    TrackSpec(
        id="walking-in-light",
        title="Walking in Light",
        artist="Nils Frahm",
        duration="4:11",
        last_used=None,
        topics=["faith", "motivational"],
    ),
    TrackSpec(id="new-season", title="New Season", artist="Hammock", duration="5:02", last_used=None, topics=["hope"]),
    TrackSpec(
        id="rise-again",
        title="Rise Again",
        artist="Ólafur Arnalds",
        duration="3:18",
        last_used=None,
        topics=["motivational", "hope"],
    ),
    TrackSpec(
        id="push-through",
        title="Push Through",
        artist="Mogwai",
        duration="4:44",
        last_used=None,
        topics=["motivational"],
    ),
]

SEED_BRAND = BrandKit(
    voice_tone=VOICE_TONE,
    banned=list(BANNED_TOPICS),
    refs=[
        StyleRef(id="ref-1", url="/media/mountains.jpg", note="mountain peaks above cloud sea at dawn", topic="faith"),
        StyleRef(id="ref-2", url="/media/valley.jpg", note="quiet valley, cool palette, no people", topic="faith"),
        StyleRef(id="ref-3", url="/media/boats.jpg", note="wooden boats on still water", topic="motivational"),
        StyleRef(id="ref-4", url="/media/hills.jpg", note="rolling hills, natural light", topic="hope"),
        StyleRef(id="ref-5", url="/media/leaves.jpg", note="tree canopy, editorial landscape", topic="motivational"),
        StyleRef(id="ref-6", url="/media/mist.jpg", note="misty forest, golden hour", topic="hope"),
        StyleRef(id="ref-7", url="/media/forest.jpg", note="dark forest, moody light", topic="faith"),
    ],
)
