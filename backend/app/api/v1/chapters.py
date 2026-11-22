"""Feature 4: Living Chapters API"""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import LivingChapter
from app.services.living_chapters import generate_living_chapters

router = APIRouter(prefix="/chapters", tags=["chapters"])


@router.get("/", response_model=list[LivingChapter])
async def get_chapters() -> list[LivingChapter]:
    """
    Generate and return all Living Chapters.

    Clusters related entries into story arcs and writes
    a narrative for each arc.
    """
    return await generate_living_chapters()
