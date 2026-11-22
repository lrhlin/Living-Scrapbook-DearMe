"""
In-memory store for entries (replace with a real DB in production).
"""
from __future__ import annotations

from app.models.schemas import Entry

_entries: dict[str, Entry] = {}


def save_entry(entry: Entry) -> Entry:
    _entries[entry.id] = entry
    return entry


def get_entry(entry_id: str) -> Entry | None:
    return _entries.get(entry_id)


def list_entries() -> list[Entry]:
    return sorted(_entries.values(), key=lambda e: e.created_at, reverse=True)


def delete_entry(entry_id: str) -> bool:
    if entry_id in _entries:
        del _entries[entry_id]
        return True
    return False
