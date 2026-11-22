"""
Feature 2: Aesthetic Learning System

Tracks user edit behaviour and updates a StyleProfile.
Provides prompt hints that reflect the user's learned aesthetic.
"""
from __future__ import annotations

from app.models.schemas import EditAction, StyleProfile

# Single in-memory style profile (one user for now)
_profile = StyleProfile()


def get_style_profile() -> StyleProfile:
    return _profile


def record_edits(actions: list[EditAction]) -> StyleProfile:
    """Update the style profile based on a batch of edit actions."""
    global _profile

    for action in actions:
        _apply_action(action)

    _profile.edit_count += len(actions)
    return _profile


def _apply_action(action: EditAction) -> None:
    """Nudge style parameters based on a single edit action."""
    t = action.action_type
    el = action.element_type

    # Deleting stickers → prefers minimalism & negative space
    if t == "delete_sticker" or (t == "delete" and el == "sticker"):
        _nudge("prefer_minimalism", +0.05)
        _nudge("prefer_negative_space", +0.05)

    # Repositioning photos into free placement → prefers collage
    if t == "reposition_photo" or (t == "reposition" and el == "photo"):
        detail = action.detail
        if detail.get("irregular", False):
            _nudge("prefer_collage", +0.05)
        else:
            _nudge("prefer_collage", -0.02)

    # Resizing a sticker to smaller → prefers minimalism
    if t == "resize" and el == "sticker":
        scale = action.detail.get("scale", 1.0)
        if isinstance(scale, (int, float)) and scale < 0.8:
            _nudge("prefer_minimalism", +0.03)

    # Picking a low-saturation color → prefers muted
    if t == "change_color":
        saturation = action.detail.get("saturation", 0.5)
        if isinstance(saturation, (int, float)):
            if saturation < 0.3:
                _nudge("prefer_muted_colors", +0.06)
            elif saturation > 0.7:
                _nudge("prefer_muted_colors", -0.06)
        hex_color = action.detail.get("hex")
        if hex_color:
            # Keep a short palette history (last 10 colors)
            palette = _profile.color_palette
            if hex_color not in palette:
                _profile.color_palette = (palette + [hex_color])[-10:]

    # Reducing text block size → prefers breathing room
    if t == "resize" and el == "text":
        scale = action.detail.get("scale", 1.0)
        if isinstance(scale, (int, float)) and scale < 0.8:
            _nudge("prefer_negative_space", +0.03)


def _nudge(field: str, delta: float) -> None:
    """Clamp-safe increment of a StyleProfile float field."""
    current = getattr(_profile, field)
    setattr(_profile, field, max(0.0, min(1.0, current + delta)))


def reset_style_profile() -> StyleProfile:
    """Reset the style profile to neutral defaults."""
    global _profile
    _profile = StyleProfile()
    return _profile
