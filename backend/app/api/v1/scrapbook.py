from __future__ import annotations

from datetime import date as CalendarDate
import re
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.services import scrapbook, scrapbook_writer
from app.services.bob_client import BobError, cli_path
from app.services.svg_stickers import SVGError

router = APIRouter(prefix="/scrapbook", tags=["scrapbook"])


class EntryCreate(BaseModel):
    title: str = Field(default="", max_length=120)
    text: str = Field(default="", max_length=20_000)
    date: CalendarDate
    sticker_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("title", "text")
    @classmethod
    def valid_xml_text(cls, value: str) -> str:
        if re.search(r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]", value):
            raise ValueError("Please remove unsupported control characters from the text.")
        return value


class WritingDraftRequest(BaseModel):
    phrase: str = Field(min_length=1, max_length=2_000)
    style: Literal["simple", "detailed", "literary", "li_bai", "hemingway", "personal"] = "simple"
    title: str = Field(default="", max_length=120)
    date: CalendarDate | None = None
    sticker_labels: list[str] = Field(default_factory=list, max_length=50)
    samples: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("phrase")
    @classmethod
    def nonblank_phrase(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Enter a phrase or a few memory notes first.")
        return value.strip()


@router.get("/stickers")
def stickers() -> list[dict]:
    return scrapbook.sticker_catalog()


@router.post("/draft")
async def create_writing_draft(payload: WritingDraftRequest) -> dict[str, str]:
    if not settings.read_bob_key() or not cli_path():
        raise HTTPException(503, "Add your IBM Bob key and finish Bob Shell setup before drafting text.")
    try:
        return await scrapbook_writer.draft_story(
            phrase=payload.phrase,
            style=payload.style,
            samples=payload.samples,
            title=payload.title,
            memory_date=payload.date.isoformat() if payload.date else "",
            sticker_labels=payload.sticker_labels,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except BobError as exc:
        raise HTTPException(503, str(exc)) from None


@router.post("/entries", status_code=201)
async def create_entry(payload: EntryCreate) -> dict:
    try:
        return await scrapbook.create_entry(payload.title, payload.text, payload.date, payload.sticker_ids)
    except (ValueError, SVGError) as exc:
        raise HTTPException(400, str(exc)) from None
    except BobError as exc:
        raise HTTPException(503, str(exc)) from None


@router.get("/entries")
def list_entries() -> list[dict]:
    return scrapbook.list_entries()


@router.get("/entries/{entry_id}")
def get_entry(entry_id: str) -> dict:
    entry = scrapbook.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Scrapbook entry not found")
    return entry


@router.get("/entries/{entry_id}/files/{filename}")
def entry_file(entry_id: str, filename: str, download: bool = False) -> FileResponse:
    entry = get_entry(entry_id)
    match = re.fullmatch(r"page-([1-9][0-9]?)\.(svg|png)", filename)
    if filename != "scrapbook.zip" and (not match or int(match[1]) > entry["page_count"]):
        raise HTTPException(404, "Scrapbook page not found")
    path = scrapbook.storage_root() / entry_id / filename
    if not path.is_file():
        raise HTTPException(404, "Scrapbook file not found")
    return FileResponse(path, filename=filename if download or filename.endswith(".zip") else None,
                        headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
                                 "X-Content-Type-Options": "nosniff"})
