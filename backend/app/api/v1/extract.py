"""Feature 3: Object Extraction API"""
from __future__ import annotations

import os
from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.models.schemas import ExtractionResult
from app.services.object_extractor import extract_objects_from_image

router = APIRouter(prefix="/extract", tags=["extract"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@router.post("/", response_model=ExtractionResult)
async def extract_objects(
    file: UploadFile = File(...),
    style: str = Form(default="watercolor"),
) -> ExtractionResult:
    """
    Upload a photo and receive a list of extracted scrapbook objects.

    - **file**: image file (JPEG, PNG, or WebP)
    - **style**: one of `watercolor`, `lineart`, `collage`, `vintage`
    """
    if style not in ("watercolor", "lineart", "collage", "vintage"):
        raise HTTPException(status_code=400, detail="Invalid style. Choose from: watercolor, lineart, collage, vintage")

    suffix = Path(file.filename or "upload.jpg").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    upload_dir = Path(settings.upload_dir) / "originals"
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = upload_dir / f"{os.urandom(8).hex()}{suffix}"

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)

    result = await extract_objects_from_image(str(dest_path), style=style)
    return result
