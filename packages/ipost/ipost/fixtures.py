from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ipost.mux import STORY_HEIGHT, STORY_WIDTH


def write_placeholder_still(path: Path, text: str = "iPost") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (STORY_WIDTH, STORY_HEIGHT), (18, 18, 18))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default(size=96)
    except TypeError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (STORY_WIDTH - (bbox[2] - bbox[0])) / 2
    y = (STORY_HEIGHT - (bbox[3] - bbox[1])) / 2
    draw.text((x, y), text, fill=(245, 240, 232), font=font)
    image.save(path, format="JPEG", quality=92)
    return path
