"""Feature 1: Memory Graph API"""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ConnectionSuggestion, MemoryGraph
from app.services.memory_graph import build_memory_graph, get_connection_suggestions

router = APIRouter(prefix="/memory-graph", tags=["memory-graph"])


@router.get("/", response_model=MemoryGraph)
def get_memory_graph() -> MemoryGraph:
    """Return the full memory graph (nodes + edges)."""
    return build_memory_graph()


@router.get("/suggestions", response_model=list[ConnectionSuggestion])
def get_suggestions() -> list[ConnectionSuggestion]:
    """Return AI-suggested connections between entries."""
    return get_connection_suggestions()
