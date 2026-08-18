from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

JobType = Literal["STORY", "REEL"]
JobStatus = Literal[
    "SCHEDULED",
    "GENERATING",
    "CRITIQUE",
    "REGENERATING",
    "APPROVED",
    "NEEDS_REVIEW",
    "REJECTED",
    "PUBLISHING",
    "PUBLISHED",
    "FAILED",
    "SKIPPED",
]
TopicSlug = str
Slot = Literal["morning", "evening"]


class PlanOutput(BaseModel):
    model_config = {"extra": "forbid"}

    topic: TopicSlug
    hook: str
    visual_prompt: str
    on_image_text: str
    caption: str = ""
    avoid: list[str] = Field(default_factory=list)


class CriticSubscores(BaseModel):
    model_config = {"extra": "forbid"}

    brand: float = Field(ge=0, le=10)
    clarity: float = Field(ge=0, le=10)
    spec: float = Field(ge=0, le=10)
    originality: float = Field(ge=0, le=10)
    safety: float = Field(ge=0, le=10)


class CritiqueOutput(BaseModel):
    model_config = {"extra": "forbid"}

    score: float = Field(ge=0, le=10)
    hard_fail: bool = False
    must_fix: str | None = None
    subscores: CriticSubscores


class TimelineStep(BaseModel):
    label: str
    sub: str
    kind: Literal["neutral", "bad", "current"] = "neutral"


class JobRecord(BaseModel):
    id: str
    type: JobType
    slot: Slot
    date: str
    publish_at: str
    topic: TopicSlug
    status: JobStatus
    still_path: str = ""
    still_url: str = ""
    video_path: str = ""
    video_url: str = ""
    caption: str = ""
    audio_id: str | None = None
    score: float = 0
    attempt: int = 0
    max_attempts: int = 3
    must_fix: str | None = None
    subscores: CriticSubscores | None = None
    timeline: list[TimelineStep] = Field(default_factory=list)
    hook: str = ""
    visual_prompt: str = ""


class TopicSpec(BaseModel):
    slug: TopicSlug
    name: str
    weight: int
    enabled: bool = True
    last_used: str | None = None
    audio_ids: list[str] = Field(default_factory=list)
    refs: list[str] = Field(default_factory=list)


class TrackSpec(BaseModel):
    id: str
    title: str
    artist: str
    topics: list[TopicSlug]
    last_used: str | None = None
    path: str = ""
    duration: str = ""
