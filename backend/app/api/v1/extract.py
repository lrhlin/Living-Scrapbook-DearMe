"""Feature 3: Object Extraction API"""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from app.models.schemas import ExtractionResult
from app.services.object_extractor import STYLE_ALIASES
from app.services.studio_jobs import get_job
from app.api.v1.studio import create

router = APIRouter(prefix="/extract", tags=["extract"])

@router.post("/", response_model=ExtractionResult)
async def extract_objects(
    request: Request,
    file: UploadFile = File(...),
    style: str = Form(default="watercolor"),
) -> ExtractionResult:
    """Compatibility endpoint for the original Next.js client; now uses Bob."""
    job = await create(file=file, style=STYLE_ALIASES.get(style, style), subject="", instructions="", count=1)
    while job["status"] not in {"done", "error"}:
        await asyncio.sleep(0.5)
        job = get_job(job["id"])
    if job["status"] == "error":
        raise HTTPException(502, job["error"])
    result = ExtractionResult(**job["result"])
    base = str(request.base_url).rstrip("/")
    result.source_image_url = base + result.source_image_url
    for obj in result.objects:
        obj.image_url = base + obj.image_url
        obj.svg_url = base + obj.svg_url
        obj.artwork_url = base + obj.artwork_url
    return result
