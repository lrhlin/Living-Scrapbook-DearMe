"""Group related journal entries into chapters with a shared theme and narrative."""
from __future__ import annotations

from itertools import combinations

from app.models.schemas import (
    ChapterEntry,
    Entry,
    LivingChapter,
)
from app.models.store import list_entries
from app.services.memory_graph import _shared_attributes


def _cluster_entries(entries: list[Entry]) -> list[list[Entry]]:
    """
    Group entries into clusters using a simple union-find approach.
    Two entries are in the same cluster if they share at least one attribute.
    """
    parent: dict[str, str] = {e.id: e.id for e in entries}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        parent[find(x)] = find(y)

    for a, b in combinations(entries, 2):
        if _shared_attributes(a, b):
            union(a.id, b.id)

    clusters: dict[str, list[Entry]] = {}
    for entry in entries:
        root = find(entry.id)
        clusters.setdefault(root, []).append(entry)

    # A chapter brings together multiple entries.
    return [c for c in clusters.values() if len(c) > 1]


def _template_narrative(entries: list[Entry], theme: str) -> str:
    """Summarize a chapter's dates, entries and shared theme."""
    sorted_entries = sorted(entries, key=lambda e: e.created_at)
    first = sorted_entries[0]
    last = sorted_entries[-1]
    count = len(entries)
    return (
        f"This chapter brings together {count} moments connected by the theme of '{theme}'. "
        f"It begins on {first.created_at.strftime('%B %d, %Y')} with \"{first.title}\" "
        f"and grows through to {last.created_at.strftime('%B %d, %Y')} with \"{last.title}\". "
        f"These entries share locations, people, or themes that reveal a continuing story in your life."
    )


async def _ai_narrative(entries: list[Entry], theme: str) -> str:
    """Write a chapter with Bob or the local summary template."""
    from app.core.config import settings
    from app.services.bob_client import BobError, run_bob
    from pathlib import Path
    from tempfile import TemporaryDirectory
    if not settings.read_bob_key():
        return _template_narrative(entries, theme)

    summaries = "\n".join(
        f"- [{e.created_at.strftime('%Y-%m-%d')}] {e.title}: {e.text[:200]}"
        for e in sorted(entries, key=lambda x: x.created_at)
    )

    prompt = (
        f"The following journal entries are connected by the theme '{theme}':\n\n"
        f"{summaries}\n\n"
        "Write a warm, 2–3 sentence narrative that tells the story arc these entries form together. "
        "Write in second person ('you') using only the supplied facts. "
        'Return only JSON with a single key: {"narrative":"your chapter narrative"}. '
        "Deliver the narrative as your final response."
    )
    root = Path(settings.upload_dir) / "chapters"
    root.mkdir(parents=True, exist_ok=True)
    try:
        with TemporaryDirectory(dir=root) as workspace:
            payload, _ = await run_bob(prompt, Path(workspace), images=False)
        narrative = payload.get("narrative")
        return narrative[:2000] if isinstance(narrative, str) and narrative.strip() else _template_narrative(entries, theme)
    except BobError:
        return _template_narrative(entries, theme)


def _infer_chapter_theme(entries: list[Entry]) -> str:
    """Pick the most prominent shared attribute as the chapter theme."""
    # Count tag frequency
    tag_counts: dict[str, int] = {}
    for e in entries:
        for t in e.tags:
            tag_counts[t.lower()] = tag_counts.get(t.lower(), 0) + 1

    if tag_counts:
        top_tag = max(tag_counts, key=lambda k: tag_counts[k])
        if tag_counts[top_tag] > 1:
            return top_tag.title()

    # Use the location for chapters centered on a place.
    locations = [e.location for e in entries if e.location]
    if locations:
        from collections import Counter
        loc = Counter(locations).most_common(1)[0][0]
        return f"Life at {loc}"

    # Use a person's name for chapters centered on shared company.
    people_counts: dict[str, int] = {}
    for e in entries:
        for p in e.people:
            people_counts[p.lower()] = people_counts.get(p.lower(), 0) + 1
    if people_counts:
        top_person = max(people_counts, key=lambda k: people_counts[k])
        return f"Time with {top_person.title()}"

    return "A Chapter of Your Life"


def _chapter_title(entries: list[Entry], theme: str) -> str:
    sorted_e = sorted(entries, key=lambda e: e.created_at)
    first_date = sorted_e[0].created_at.strftime("%B %Y")
    last_date = sorted_e[-1].created_at.strftime("%B %Y")
    if first_date == last_date:
        return f"{theme} · {first_date}"
    return f"{theme} · {first_date} – {last_date}"


async def generate_living_chapters(entries: list[Entry] | None = None) -> list[LivingChapter]:
    """Generate all living chapters from all stored entries."""
    if entries is None:
        entries = list_entries()

    if len(entries) < 2:
        return []

    clusters = _cluster_entries(entries)
    chapters: list[LivingChapter] = []

    for cluster in clusters:
        theme = _infer_chapter_theme(cluster)
        title = _chapter_title(cluster, theme)
        narrative = await _ai_narrative(cluster, theme)

        chapter_entries = [
            ChapterEntry(
                entry_id=e.id,
                title=e.title,
                date=e.created_at.strftime("%Y-%m-%d"),
                summary=e.text[:150] + ("…" if len(e.text) > 150 else ""),
            )
            for e in sorted(cluster, key=lambda x: x.created_at)
        ]

        chapters.append(
            LivingChapter(
                title=title,
                narrative=narrative,
                entries=chapter_entries,
                theme=theme,
            )
        )

    return chapters
