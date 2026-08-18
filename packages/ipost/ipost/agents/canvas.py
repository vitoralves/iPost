from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from ipost.fixtures import write_placeholder_still
from ipost.mux import STORY_HEIGHT, STORY_WIDTH
from ipost.overlay import apply_logo
from ipost.settings import Settings

REF_LIMIT = 4


class StillError(RuntimeError):
    pass


CanvasError = StillError


def _resize_to_story(data: bytes, destination: Path) -> Path:
    from PIL import Image

    destination.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(BytesIO(data)).convert("RGB")
    image = image.resize((STORY_WIDTH, STORY_HEIGHT))
    image.save(destination, format="JPEG", quality=92)
    return destination


def _reference_files(images: list[bytes]) -> list[BytesIO]:
    files: list[BytesIO] = []
    for index, data in enumerate(images[:REF_LIMIT]):
        if not data:
            continue
        buf = BytesIO(data)
        buf.name = f"ref-{index}.png"
        files.append(buf)
    return files


def generate_still(
    settings: Settings,
    prompt: str,
    destination: Path,
    *,
    stamp_logo: bool = True,
    references: list[bytes] | None = None,
) -> Path:
    if settings.ipost_mock_bedrock:
        write_placeholder_still(destination, prompt[:48] or "iPost")
        if stamp_logo:
            return apply_logo(destination, destination)
        return destination
    if not settings.openai_api_key:
        raise StillError("OPENAI_API_KEY is required to generate stills")

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key, timeout=180.0)
    files = _reference_files(references or [])
    if files:
        response = client.images.edit(
            model=settings.openai_image_model_id,
            image=files,
            prompt=prompt,
            size="1024x1536",
            quality="high",
            n=1,
        )
    else:
        response = client.images.generate(
            model=settings.openai_image_model_id,
            prompt=prompt,
            size="1024x1536",
            quality="high",
            n=1,
        )
    items = response.data or []
    if not items:
        raise StillError("Image model returned no images")
    raw = items[0].b64_json
    if not raw:
        raise StillError("Image model returned an empty image")
    _resize_to_story(base64.b64decode(raw), destination)
    if stamp_logo:
        return apply_logo(destination, destination)
    return destination
