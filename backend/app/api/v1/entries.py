"""Entries CRUD — the base resource for all features."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import Entry, EntryCreate
from app.models.store import delete_entry, get_entry, list_entries, save_entry

router = APIRouter(prefix="/entries", tags=["entries"])


@router.post("/", response_model=Entry, status_code=201)
def create_entry(payload: EntryCreate) -> Entry:
    entry = Entry(**payload.model_dump())
    return save_entry(entry)


@router.get("/", response_model=list[Entry])
def read_entries() -> list[Entry]:
    return list_entries()


@router.get("/{entry_id}", response_model=Entry)
def read_entry(entry_id: str) -> Entry:
    entry = get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.delete("/{entry_id}", status_code=200)
def remove_entry(entry_id: str) -> dict:
    if not delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"deleted": entry_id}
