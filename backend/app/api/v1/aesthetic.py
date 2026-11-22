"""Feature 2: Aesthetic Learning API"""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import StyleFeedback, StyleProfile
from app.services.aesthetic_learner import (
    get_style_profile,
    record_edits,
    reset_style_profile,
)

router = APIRouter(prefix="/style", tags=["style"])


@router.get("/profile", response_model=StyleProfile)
def read_style_profile() -> StyleProfile:
    """Return the current learned style profile."""
    return get_style_profile()


@router.get("/profile/hint")
def read_style_hint() -> dict[str, str]:
    """Return a text prompt hint derived from the style profile."""
    profile = get_style_profile()
    return {"hint": profile.to_prompt_hint()}


@router.post("/feedback", response_model=StyleProfile)
def submit_feedback(payload: StyleFeedback) -> StyleProfile:
    """Submit edit actions to update the style profile."""
    return record_edits(payload.actions)


@router.delete("/profile", response_model=StyleProfile)
def clear_style_profile() -> StyleProfile:
    """Reset the style profile to neutral defaults."""
    return reset_style_profile()
