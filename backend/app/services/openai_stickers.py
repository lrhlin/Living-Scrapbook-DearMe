"""Create transparent raster stickers from reference photos with OpenAI Images."""
from __future__ import annotations

import base64
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
import time

import httpx
from PIL import Image

from app.core.config import settings
from app.models.schemas import ExtractedObject, ExtractionResult
from app.services.object_extractor import STYLES


class OpenAIError(RuntimeError):
    pass


async def edit_image(reference: Path, prompt: str, count: int) -> dict:
    key = settings.read_openai_key()
    if not key:
        raise OpenAIError("Add your OpenAI API key to oaikey.txt to create PNG stickers.")
    try:
        async with httpx.AsyncClient(timeout=settings.openai_timeout_seconds) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/edits",
                headers={"Authorization": f"Bearer {key}"},
                data={"model": settings.openai_image_model, "prompt": prompt, "n": str(count),
                      "size": "1024x1024", "quality": settings.openai_image_quality,
                      "background": "transparent", "output_format": "png"},
                files={"image": ("reference.png", reference.read_bytes(), "image/png")},
            )
    except httpx.TimeoutException:
        raise OpenAIError("Image generation timed out. Try one sticker at a time.") from None
    except httpx.HTTPError:
        raise OpenAIError("Check your connection and try generating again.") from None
    if response.is_error:
        if response.status_code in {401, 403}:
            raise OpenAIError("Check your OpenAI key and image-model access, then try again.")
        if response.status_code == 429:
            raise OpenAIError("Check your OpenAI credit balance or wait before trying again.")
        raise OpenAIError("Try generating again with a simpler subject or shorter instructions.")
    return response.json()


async def extract_raster_stickers(
    image_path: str, style: str, *, subject: str = "", instructions: str = "",
    count: int = 1, phase: Callable[[str], None] | None = None,
) -> ExtractionResult:
    reference = Path(image_path)
    prompt = f"""Turn the subject in this reference photo into one polished scrapbook sticker.
Subject: {subject or 'the most distinctive main subject in the photo'}.
Art direction: {STYLES[style]}. Create a detailed raster illustration with natural, recognizable proportions, colors and distinctive features from the reference.
Compose the subject as a complete, centered keepsake on a transparent background, with generous clear space around it. Follow the subject's contour with a clean, even warm-white die-cut sticker border. Keep fine features such as ears and whiskers intact and the silhouette coherent. Render rich, carefully finished artwork that looks good at small sizes.
Additional artwork preferences: {instructions or 'Keep the composition focused on the subject.'}
Deliver a single isolated sticker per image. Preserve the requested framing, including a face-and-ears portrait when requested."""
    started = time.monotonic()
    if phase:
        phase("generating")
    payload = await edit_image(reference, prompt, count)
    images = payload.get("data", [])
    if len(images) != count:
        raise OpenAIError("Try generating your requested sticker variations again.")
    if phase:
        phase("finishing")
    base = f"/api/v1/studio/jobs/{reference.parent.name}/files"
    objects = []
    label = subject.strip() or "Photo keepsake"
    for index, item in enumerate(images):
        with Image.open(BytesIO(base64.b64decode(item["b64_json"]))) as source:
            source.convert("RGBA").save(reference.parent / f"sticker-{index}.png", format="PNG")
        objects.append(ExtractedObject(
            label=(label + (f" · {index + 1}" if count > 1 else ""))[:80], style=style,
            description="An OpenAI illustration inspired by your photo.", image_url=f"{base}/sticker-{index}.png",
            artwork_url=f"{base}/sticker-{index}.png", provider="openai", format="png",
        ))
    usage = {**payload.get("usage", {}), "provider": "openai", "model": settings.openai_image_model,
             "elapsed_seconds": round(time.monotonic() - started, 2)}
    return ExtractionResult(source_image_url=f"{base}/original.png", objects=objects, usage=usage)
