"""
Feature 3: Real Objects → Scrapbook Materials

1. Accepts an uploaded image.
2. Uses GPT-4o Vision to identify objects in the photo.
3. For each object, calls DALL·E 3 to generate a sticker-style asset.
4. Returns a list of independently usable scrapbook elements.

If OPENAI_API_KEY is not set, runs in demo/mock mode.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

from app.core.config import settings
from app.models.schemas import ExtractedObject, ExtractionResult

STYLE_PROMPTS: dict[str, str] = {
    "watercolor": "watercolor painting style, soft edges, transparent washes, white background, isolated object, no text",
    "lineart":    "minimalist line art, black ink on white background, isolated object, clean strokes, no fill",
    "collage":    "vintage magazine cutout style, slight texture, isolated object, white background",
    "vintage":    "vintage illustration style, aged paper texture, muted colors, isolated object, white background",
}


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def extract_objects_from_image(
    image_path: str,
    style: str = "watercolor",
) -> ExtractionResult:
    """Main entry point: analyse photo and generate sticker assets."""

    if not settings.openai_api_key:
        return _mock_result(image_path, style)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # ── Step 1: identify objects via GPT-4o Vision ──
    b64 = _encode_image(image_path)
    vision_response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Look at this photo and list up to 6 distinct objects that would make "
                            "interesting scrapbook stickers (e.g. coffee cup, receipt, flower, candle). "
                            "Reply with a JSON array of short English labels only, like: "
                            '[\"coffee cup\", \"receipt\", \"daisy\"]'
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ],
        max_tokens=200,
    )

    import json
    raw = vision_response.choices[0].message.content or "[]"
    # Strip markdown fences if present
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        labels: list[str] = json.loads(raw)
    except Exception:
        labels = ["object"]

    # ── Step 2: generate a sticker image for each object ──
    style_hint = STYLE_PROMPTS.get(style, STYLE_PROMPTS["watercolor"])
    objects: list[ExtractedObject] = []

    upload_dir = Path(settings.upload_dir) / "stickers"
    upload_dir.mkdir(parents=True, exist_ok=True)

    for label in labels[:6]:
        prompt = f"{label}, {style_hint}"
        img_response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = img_response.data[0].url or ""
        objects.append(
            ExtractedObject(
                label=label,
                style=style,
                image_url=image_url,
                description=f"{label.title()} in {style} style",
            )
        )

    return ExtractionResult(source_image_url=image_path, objects=objects)


def _mock_result(image_path: str, style: str) -> ExtractionResult:
    """Return demo data when no API key is configured."""
    mock_labels = ["coffee cup", "receipt", "flower", "candle"]
    objects = [
        ExtractedObject(
            label=label,
            style=style,
            image_url="",
            description=f"{label.title()} in {style} style (demo)",
        )
        for label in mock_labels
    ]
    return ExtractionResult(source_image_url=image_path, objects=objects)
