"""
Data models for the entire application.
Using simple in-memory + file-based storage (no database required to run locally).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Shared / Entry models
# ─────────────────────────────────────────────

class EntryCreate(BaseModel):
    title: str
    text: str = ""
    location: str = ""
    people: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)


class Entry(EntryCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# Memory Graph models
# ─────────────────────────────────────────────

class MemoryNode(BaseModel):
    entry_id: str
    title: str
    location: str = ""
    people: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""


class MemoryEdge(BaseModel):
    source: str          # entry_id
    target: str          # entry_id
    reason: str          # human-readable connection reason
    weight: float = 1.0  # connection strength 0–1


class MemoryGraph(BaseModel):
    nodes: list[MemoryNode]
    edges: list[MemoryEdge]


class ConnectionSuggestion(BaseModel):
    entry_a: str
    entry_b: str
    reason: str
    suggested_theme: str


# ─────────────────────────────────────────────
# Aesthetic / Style models
# ─────────────────────────────────────────────

class EditAction(BaseModel):
    action_type: str           # "delete_sticker" | "reposition_photo" | "change_color" | "resize"
    element_type: str          # "sticker" | "photo" | "text" | "background"
    detail: dict[str, Any] = Field(default_factory=dict)


class StyleFeedback(BaseModel):
    entry_id: str
    actions: list[EditAction]


class StyleProfile(BaseModel):
    user_id: str = "default"
    prefer_minimalism: float = 0.5      # 0=maximalist, 1=minimal
    prefer_collage: float = 0.5         # 0=grid, 1=collage
    prefer_muted_colors: float = 0.5    # 0=vivid, 1=muted
    prefer_negative_space: float = 0.5  # 0=dense, 1=airy
    color_palette: list[str] = Field(default_factory=list)
    edit_count: int = 0

    def to_prompt_hint(self) -> str:
        hints = []
        if self.prefer_minimalism > 0.6:
            hints.append("minimalist, lots of white space")
        elif self.prefer_minimalism < 0.4:
            hints.append("maximalist, richly decorated")

        if self.prefer_collage > 0.6:
            hints.append("irregular collage arrangement")
        else:
            hints.append("clean grid layout")

        if self.prefer_muted_colors > 0.6:
            hints.append("muted low-saturation palette")
        elif self.prefer_muted_colors < 0.4:
            hints.append("vibrant saturated colors")

        if self.prefer_negative_space > 0.6:
            hints.append("generous negative space")

        return ", ".join(hints) if hints else "balanced aesthetic"


# ─────────────────────────────────────────────
# Object Extraction models
# ─────────────────────────────────────────────

class ExtractedObject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str                  # "coffee cup", "receipt", etc.
    style: str                  # "watercolor" | "lineart" | "collage" | "vintage"
    image_url: str = ""         # URL to the generated sticker asset
    description: str = ""


class ExtractionResult(BaseModel):
    source_image_url: str
    objects: list[ExtractedObject]


# ─────────────────────────────────────────────
# Living Chapters models
# ─────────────────────────────────────────────

class ChapterEntry(BaseModel):
    entry_id: str
    title: str
    date: str
    summary: str


class LivingChapter(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    narrative: str
    entries: list[ChapterEntry]
    theme: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
