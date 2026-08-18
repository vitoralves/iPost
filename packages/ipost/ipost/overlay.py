from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ipost.mux import STORY_HEIGHT, STORY_WIDTH


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def burn_text(source: Path, text: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert("RGB")
    image = image.resize((STORY_WIDTH, STORY_HEIGHT))
    draw = ImageDraw.Draw(image)
    font = _font(64)
    max_width = STORY_WIDTH - 120
    lines = _wrap(draw, text.strip(), font, max_width)
    if not lines:
        image.save(destination, format="JPEG", quality=92)
        return destination
    heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    block_height = sum(heights) + 16 * (len(lines) - 1)
    y = STORY_HEIGHT - 280 - block_height
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle((0, y - 40, STORY_WIDTH, y + block_height + 48), fill=(18, 16, 14, 140))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(image)
    cursor = y
    for line, width, height in zip(lines, widths, heights, strict=True):
        x = (STORY_WIDTH - width) / 2
        draw.text((x, cursor), line, fill=(243, 239, 230), font=font)
        cursor += height + 16
    image.save(destination, format="JPEG", quality=92)
    return destination
