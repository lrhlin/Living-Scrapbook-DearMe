"""Queue sticker generations and save their artwork, previews and usage."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from app.core.config import settings
from app.services.bob_client import BobError
from app.services.object_extractor import extract_objects_from_image
from app.services.openai_stickers import OpenAIError, extract_raster_stickers
from app.services.svg_stickers import SVGError

_active: dict[str, dict] = {}
_tasks: set[asyncio.Task] = set()
_gate = asyncio.Semaphore(1)


def job_root() -> Path:
    root = Path(settings.upload_dir) / "studio"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _save(job: dict) -> None:
    folder = job_root() / job["id"]
    pending = folder / "job.pending"
    pending.write_text(json.dumps(job, indent=2))
    pending.replace(folder / "job.json")


def get_job(job_id: str) -> dict | None:
    if job_id in _active:
        return _active[job_id]
    try:
        job = json.loads((job_root() / job_id / "job.json").read_text())
    except (OSError, ValueError):
        return None
    if job.get("status") in {"queued", "generating", "finishing"}:
        job.update(status="error", error="The local server restarted before this generation finished. You can start a new request.")
        _save(job)
    return job


def list_jobs() -> list[dict]:
    jobs = []
    for path in sorted(job_root().glob("*/job.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:60]:
        job = get_job(path.parent.name)
        if job and job["status"] in {"done", "error"}:
            jobs.append(job)
    return jobs


def normalize_image(content: bytes, destination: Path) -> None:
    try:
        with Image.open(BytesIO(content)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > 25_000_000:
                raise ValueError("Choose a JPG, PNG or WebP image under 25 megapixels.")
            image = ImageOps.exif_transpose(source).convert("RGBA")
            image.thumbnail((1400, 1400))
            image.info.clear()
            image.save(destination, format="PNG")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError("Choose a JPG, PNG or WebP photo.") from None


async def _generate(job: dict) -> None:
    try:
        async with _gate:
            def phase(status: str) -> None:
                job["status"] = status
                _save(job)
            generate = extract_raster_stickers if job["provider"] == "openai" else extract_objects_from_image
            result = await generate(
                str(job_root() / job["id"] / "original.png"), job["style"],
                subject=job["subject"], instructions=job["instructions"], count=job["count"], phase=phase,
            )
            job.update(status="done", result=result.model_dump(), completed_at=datetime.now(timezone.utc).isoformat())
    except (BobError, OpenAIError, SVGError, ValueError) as exc:
        job.update(status="error", error=str(exc))
    except Exception:
        job.update(status="error", error="Try generating your sticker again.")
    finally:
        _save(job)
        _active.pop(job["id"], None)


async def create_job(content: bytes, *, style: str, subject: str, instructions: str, count: int, provider: str) -> dict:
    if len(_active) >= 3:
        raise BobError("Three generations are already queued. Wait for one to finish.")
    job_id = uuid4().hex
    folder = job_root() / job_id
    folder.mkdir()
    try:
        await asyncio.to_thread(normalize_image, content, folder / "original.png")
    except ValueError:
        folder.rmdir()
        raise
    job = {
        "id": job_id, "status": "queued", "provider": provider, "style": style, "subject": subject,
        "instructions": instructions, "count": count, "created_at": datetime.now(timezone.utc).isoformat(),
        "source_image_url": f"/api/v1/studio/jobs/{job_id}/files/original.png",
    }
    _active[job_id] = job
    _save(job)
    task = asyncio.create_task(_generate(job))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return job
