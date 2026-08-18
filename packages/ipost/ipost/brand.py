from __future__ import annotations

from pydantic import BaseModel, Field

from ipost.agents.templates import BANNED_TOPICS, VOICE_TONE


class StyleRef(BaseModel):
    id: str
    url: str = ""
    path: str = ""
    note: str = ""
    topic: str = ""


class BrandKit(BaseModel):
    voice_tone: str = VOICE_TONE
    banned: list[str] = Field(default_factory=lambda: list(BANNED_TOPICS))
    refs: list[StyleRef] = Field(default_factory=list)

    def banned_text(self) -> str:
        return "; ".join(item for item in self.banned if item.strip())

    def refs_for_topic(self, topic: str) -> list[StyleRef]:
        slug = topic.strip()
        return [ref for ref in self.refs if ref.topic == slug]

    def ref_lines(self, topic: str | None = None) -> list[str]:
        refs = self.refs_for_topic(topic) if topic else self.refs
        lines: list[str] = []
        for ref in refs:
            if not ref.url.strip() and not ref.path:
                continue
            note = ref.note.strip() or "style reference"
            label = f"{ref.topic} · {note}" if ref.topic else note
            lines.append(f"{label} ({ref.url})" if ref.url else label)
        return lines


def load_brand_kit(settings=None) -> BrandKit:
    from ipost.config_store import load_brand_kit as _load

    return _load(settings)


def save_brand_kit(kit: BrandKit, settings=None) -> BrandKit:
    from ipost.config_store import save_brand_kit as _save

    return _save(kit, settings)


def apply_brand(template: str, kit: BrandKit | None = None) -> str:
    kit = kit or load_brand_kit()
    return template.replace("{voice_tone}", kit.voice_tone).replace("{banned}", kit.banned_text())
