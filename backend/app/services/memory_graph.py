"""Connect journal entries through shared locations, people and tags."""
from __future__ import annotations

from itertools import combinations

from app.models.schemas import (
    Entry,
    MemoryEdge,
    MemoryGraph,
    MemoryNode,
    ConnectionSuggestion,
)
from app.models.store import list_entries


def _shared_attributes(a: Entry, b: Entry) -> list[str]:
    """Return a list of reasons two entries are related."""
    reasons = []
    if a.location and b.location and a.location.lower() == b.location.lower():
        reasons.append(f"same location: {a.location}")
    shared_people = set(p.lower() for p in a.people) & set(p.lower() for p in b.people)
    if shared_people:
        reasons.append(f"shared people: {', '.join(shared_people)}")
    shared_tags = set(t.lower() for t in a.tags) & set(t.lower() for t in b.tags)
    if shared_tags:
        reasons.append(f"shared tags: {', '.join(shared_tags)}")
    return reasons


def _connection_weight(reasons: list[str]) -> float:
    """More shared attributes → stronger connection."""
    return min(1.0, len(reasons) * 0.4)


def build_memory_graph(entries: list[Entry] | None = None) -> MemoryGraph:
    """Build the full memory graph for all stored entries."""
    if entries is None:
        entries = list_entries()

    nodes = [
        MemoryNode(
            entry_id=e.id,
            title=e.title,
            location=e.location,
            people=e.people,
            tags=e.tags,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]

    edges: list[MemoryEdge] = []
    for a, b in combinations(entries, 2):
        reasons = _shared_attributes(a, b)
        if reasons:
            weight = _connection_weight(reasons)
            reason_str = "; ".join(reasons)
            edges.append(
                MemoryEdge(
                    source=a.id,
                    target=b.id,
                    reason=reason_str,
                    weight=weight,
                )
            )

    return MemoryGraph(nodes=nodes, edges=edges)


def get_connection_suggestions(entries: list[Entry] | None = None) -> list[ConnectionSuggestion]:
    """Suggest connections between entries with shared details."""
    if entries is None:
        entries = list_entries()

    suggestions: list[ConnectionSuggestion] = []
    for a, b in combinations(entries, 2):
        reasons = _shared_attributes(a, b)
        if reasons:
            theme = _infer_theme(a, b, reasons)
            suggestions.append(
                ConnectionSuggestion(
                    entry_a=a.id,
                    entry_b=b.id,
                    reason="; ".join(reasons),
                    suggested_theme=theme,
                )
            )

    # Sort by number of connection reasons (most connected first)
    return sorted(suggestions, key=lambda s: len(s.reason.split(";")), reverse=True)


def _infer_theme(a: Entry, b: Entry, reasons: list[str]) -> str:
    """Generate a simple suggested theme name from the connection reasons."""
    if any("location" in r for r in reasons):
        loc = a.location or b.location
        return f"Memories at {loc}"
    if any("people" in r for r in reasons):
        # Extract first shared person name
        shared = set(p.lower() for p in a.people) & set(p.lower() for p in b.people)
        name = next(iter(shared)).title()
        return f"Moments with {name}"
    if any("tags" in r for r in reasons):
        shared = set(t.lower() for t in a.tags) & set(t.lower() for t in b.tags)
        tag = next(iter(shared))
        return f"My {tag.title()} Story"
    return "Connected Memories"
