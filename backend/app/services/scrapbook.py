"""Saved scrapbook entries with deterministic text flow and sticker pagination."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unicodedata
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from PIL import ImageFont

from app.core.config import PROJECT_ROOT, settings
from app.services import studio_jobs
from app.services.object_extractor import render_svg
from app.services.svg_stickers import NS, validate_svg

ET.register_namespace("", NS)
PAGE_W, PAGE_H = 900, 1200
MARGIN, BOTTOM, LINE_HEIGHT = 72, 1110, 31
ROW_HEIGHT, ROW_GAP, COL_GAP = 252, 22, 28
THEME_ROW_HEIGHT = {"minimal": 470, "botanical": 490, "celebration": 500, "travel": 460, "cozy": 500, "vintage": 490}
SAMPLES = {"cat": "Tabby cat", "tree": "Christmas tree", "school": "School building"}
ID_PATTERN = r"[a-f0-9]{32}"
THEMES = {
    "minimal": {"label": "Minimal", "paper": "#fffdf8", "frame": "#d9ded5", "title": "#253d36", "text": "#46534e", "muted": "#77827b", "accent": "#dbe0d7", "card1": "#f0f1ec", "card2": "#f7f5ef"},
    "botanical": {"label": "Botanical", "paper": "#f7f7ef", "frame": "#aab99b", "title": "#3e5941", "text": "#4c5b4b", "muted": "#73836c", "accent": "#b9c8a9", "card1": "#e6eddf", "card2": "#eff0e5"},
    "celebration": {"label": "Celebration", "paper": "#fff8ed", "frame": "#d79672", "title": "#874d42", "text": "#5e4c46", "muted": "#a46c54", "accent": "#e9c69a", "card1": "#f5dfd1", "card2": "#f7eccf"},
    "travel": {"label": "Travel", "paper": "#f1f6f6", "frame": "#83a8ae", "title": "#345c68", "text": "#405a61", "muted": "#63828b", "accent": "#afc8cb", "card1": "#dbe9e9", "card2": "#f0e7d5"},
    "cozy": {"label": "Cozy", "paper": "#fff8f2", "frame": "#d3a99a", "title": "#79574e", "text": "#5e504b", "muted": "#a27668", "accent": "#e7cfc4", "card1": "#f1e2da", "card2": "#f7ecdf"},
    "vintage": {"label": "Vintage", "paper": "#f5eedf", "frame": "#9c8056", "title": "#634d32", "text": "#574a3d", "muted": "#887149", "accent": "#d2bf96", "card1": "#e9dcc1", "card2": "#eee5d3"},
}


def storage_root() -> Path:
    root = Path(settings.upload_dir) / "scrapbook"
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_sticker(sticker_id: str) -> tuple[dict, Path]:
    if sticker_id.startswith("example:"):
        slug = sticker_id.removeprefix("example:")
        if slug in SAMPLES:
            path = PROJECT_ROOT / "artifacts/bob-sticker-examples" / f"{slug}-sticker.svg"
            if path.is_file():
                return {"id": sticker_id, "label": SAMPLES[slug], "source": "Sample sticker",
                        "image_url": f"/api/v1/studio/examples/{slug}/png"}, path
    match = re.fullmatch(rf"job:({ID_PATTERN}):([0-2])", sticker_id)
    if match:
        job_id, index = match[1], int(match[2])
        job = studio_jobs.get_job(job_id)
        if job and job.get("status") == "done":
            objects = job.get("result", {}).get("objects", [])
            path = studio_jobs.job_root() / job_id / f"sticker-{index}.svg"
            if index < len(objects) and path.is_file():
                return {"id": sticker_id, "label": objects[index]["label"], "source": "Your sticker",
                        "image_url": objects[index]["image_url"]}, path
    raise ValueError("Refresh the sticker picker and select your stickers again.")


def sticker_catalog() -> list[dict]:
    identifiers = []
    for job in studio_jobs.list_jobs():
        if job.get("status") == "done":
            identifiers.extend(f"job:{job['id']}:{i}" for i in range(len(job.get("result", {}).get("objects", []))))
    identifiers.extend(f"example:{slug}" for slug in SAMPLES)
    result = []
    for sticker_id in identifiers:
        try:
            item, _ = resolve_sticker(sticker_id)
            result.append(item)
        except ValueError:
            continue
    return result


@lru_cache(maxsize=8)
def _font(size: int, title: bool = False):
    candidates = (
        ["/System/Library/Fonts/Supplemental/Georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]
        if title else
        ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


@lru_cache(maxsize=8192)
def _char_width(char: str, size: int, title: bool) -> float:
    width = _font(size, title).getlength(char)
    return max(width, size) if unicodedata.east_asian_width(char) in {"W", "F"} else width


def text_width(text: str, size: int = 20, title: bool = False) -> float:
    # Reserve a full em for wide glyphs in multilingual text.
    return sum(_char_width(char, size, title) for char in text)


def wrap_text(text: str, width: float, size: int = 20, title: bool = False) -> list[str]:
    lines: list[str] = []
    for paragraph in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not paragraph.strip():
            if lines and lines[-1]:
                lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if text_width(candidate, size, title) <= width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            while text_width(word, size, title) > width:
                low, high = 1, len(word)
                while low < high:
                    middle = (low + high + 1) // 2
                    if text_width(word[:middle], size, title) <= width:
                        low = middle
                    else:
                        high = middle - 1
                lines.append(word[:low])
                word = word[low:]
            current = word
        if current:
            lines.append(current)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def paginate(title: str, text: str, sticker_count: int, theme_id: str = "minimal") -> list[dict]:
    title_lines = wrap_text(title, PAGE_W - 2 * MARGIN, 33, True)
    start_y = (168 if theme_id == "celebration" else 143) + len(title_lines) * 40
    lines = wrap_text(text, PAGE_W - 2 * MARGIN - 12)
    rows = [list(range(i, min(i + 2, sticker_count))) for i in range(0, sticker_count, 2)]
    row_height = THEME_ROW_HEIGHT.get(theme_id, ROW_HEIGHT)
    pages: list[dict] = []

    def new_page():
        if len(pages) >= 60:
            raise ValueError("This entry is too long. Please split it into smaller scrapbook entries.")
        page = {"title_lines": title_lines, "blocks": []}
        pages.append(page)
        return page, start_y

    page, cursor = new_page()
    full_capacity = int((BOTTOM - start_y) // LINE_HEIGHT)
    line_index = row_index = 0
    while line_index < len(lines) or row_index < len(rows):
        if line_index < len(lines):
            capacity = int((BOTTOM - cursor) // LINE_HEIGHT)
            if capacity < min(2, len(lines) - line_index):
                page, cursor = new_page()
                capacity = int((BOTTOM - cursor) // LINE_HEIGHT)
            amount = min(6 if row_index < len(rows) else capacity, capacity, len(lines) - line_index)
            # Keep short paragraphs together between sticker rows and page breaks.
            if line_index + amount < len(lines) and lines[line_index + amount] and lines[line_index + amount - 1]:
                breaks = [i for i in range(amount) if not lines[line_index + i]]
                if breaks:
                    amount = breaks[-1] + 1
                else:
                    paragraph_end = next((i for i in range(line_index, len(lines)) if not lines[i]), len(lines))
                    paragraph_length = paragraph_end - line_index
                    if paragraph_length <= capacity:
                        amount = paragraph_length
                    elif paragraph_length <= full_capacity and capacity < full_capacity:
                        page, cursor = new_page()
                        continue
                    elif paragraph_length - amount == 1 and amount > 2:
                        amount -= 1
            page["blocks"].append({"type": "text", "x": MARGIN, "y": cursor,
                                   "height": amount * LINE_HEIGHT, "lines": lines[line_index:line_index + amount]})
            line_index += amount
            cursor += amount * LINE_HEIGHT
            if row_index < len(rows):
                cursor += 18
        if row_index < len(rows):
            if cursor + row_height > BOTTOM:
                page, cursor = new_page()
            page["blocks"].append({"type": "stickers", "x": MARGIN, "y": cursor,
                                   "height": row_height, "indices": rows[row_index]})
            row_index += 1
            cursor += row_height + ROW_GAP
    return pages


def _node(parent: ET.Element, name: str, attrs: dict | None = None, text: str | None = None):
    node = ET.SubElement(parent, f"{{{NS}}}{name}", {k: str(v) for k, v in (attrs or {}).items()})
    if text is not None:
        node.text = text
    return node


def _shape(parent: ET.Element, shape: str, x: float, y: float, width: float, height: float,
           attrs: dict | None = None) -> ET.Element:
    options = attrs or {}
    if shape == "ellipse":
        return _node(parent, "ellipse", {**options, "cx": x + width / 2, "cy": y + height / 2,
                                           "rx": width / 2, "ry": height / 2})
    if shape == "diamond":
        points = f"{x + width / 2},{y} {x + width},{y + height / 2} {x + width / 2},{y + height} {x},{y + height / 2}"
        return _node(parent, "polygon", {**options, "points": points})
    if shape == "arch":
        radius = min(width / 2, height * 0.42)
        path = f"M{x} {y + height} V{y + radius} Q{x} {y} {x + radius} {y} H{x + width - radius} Q{x + width} {y} {x + width} {y + radius} V{y + height} Z"
        return _node(parent, "path", {**options, "d": path})
    radius = 3 if shape == "postcard" else min(22, width * 0.08, height * 0.08)
    return _node(parent, "rect", {**options, "x": x, "y": y, "width": width, "height": height, "rx": radius})


def _clip_shape(parent: ET.Element, shape: str) -> ET.Element:
    if shape == "ellipse":
        return _node(parent, "ellipse", {"cx": 0.5, "cy": 0.5, "rx": 0.5, "ry": 0.5})
    if shape == "diamond":
        return _node(parent, "polygon", {"points": "0.5,0 1,0.5 0.5,1 0,0.5"})
    if shape == "arch":
        return _node(parent, "path", {"d": "M0 1 V0.42 Q0 0 0.42 0 H0.58 Q1 0 1 0.42 V1 Z"})
    return _node(parent, "rect", {"x": 0, "y": 0, "width": 1, "height": 1,
                                  "rx": 0.025 if shape == "postcard" else 0.055})


def _sticker_placements(theme_id: str, count: int, y: float, height: float) -> list[dict]:
    if theme_id == "botanical":
        return ([{"x": 458, "y": y + 4, "width": 266, "height": height - 60, "shape": "ellipse", "rotation": 2}]
                if count == 1 else [
                    {"x": 174, "y": y + 18, "width": 230, "height": height - 68, "shape": "ellipse", "rotation": -3},
                    {"x": 500, "y": y + 3, "width": 240, "height": height - 68, "shape": "diamond", "rotation": 2},
                ])
    if theme_id == "celebration":
        return ([{"x": 240, "y": y, "width": 420, "height": height, "shape": "arch", "rotation": 0}]
                if count == 1 else [
                    {"x": 128, "y": y + 5, "width": 350, "height": height - 10, "shape": "arch", "rotation": -2},
                    {"x": 518, "y": y + 36, "width": 220, "height": height - 150, "shape": "diamond", "rotation": 4},
                ])
    if theme_id == "travel":
        return ([{"x": 126, "y": y + 8, "width": 648, "height": height - 16, "shape": "postcard", "rotation": 0}]
                if count == 1 else [
                    {"x": 91, "y": y + 7, "width": 456, "height": height - 14, "shape": "postcard", "rotation": -1},
                    {"x": 584, "y": y + 28, "width": 164, "height": height - 116, "shape": "ellipse", "rotation": 3},
                ])
    if theme_id == "cozy":
        return ([{"x": 268, "y": y, "width": 364, "height": height, "shape": "polaroid", "rotation": -2}]
                if count == 1 else [
                    {"x": 118, "y": y + 2, "width": 324, "height": height - 4, "shape": "polaroid", "rotation": -3},
                    {"x": 478, "y": y + 20, "width": 236, "height": height - 40, "shape": "polaroid", "rotation": 4},
                ])
    if theme_id == "vintage":
        return ([{"x": 306, "y": y + 1, "width": 288, "height": height - 60, "shape": "ellipse", "rotation": 0}]
                if count == 1 else [
                    {"x": 146, "y": y + 12, "width": 236, "height": height - 68, "shape": "ellipse", "rotation": -2},
                    {"x": 518, "y": y + 12, "width": 236, "height": height - 68, "shape": "ellipse", "rotation": 2},
                ])
    return ([{"x": 424, "y": y + 8, "width": 366, "height": height - 16, "shape": "rounded", "rotation": 0}]
            if count == 1 else [
                {"x": 88, "y": y + 8, "width": 336, "height": height - 16, "shape": "rounded", "rotation": -1},
                {"x": 474, "y": y + 8, "width": 336, "height": height - 58, "shape": "diamond", "rotation": 1},
            ])


def _draw_sticker(root: ET.Element, defs: ET.Element, entry: dict, artwork: list[ET.Element],
                  sticker_index: int, page_index: int, theme: dict, theme_id: str,
                  placement: dict) -> None:
    x, y = placement["x"], placement["y"]
    width, height = placement["width"], placement["height"]
    rotation = placement.get("rotation", 0)
    group_attrs = {}
    if rotation:
        group_attrs["transform"] = f"rotate({rotation} {x + width / 2} {y + height / 2})"
    group = _node(root, "g", group_attrs)
    shape = placement["shape"]
    if shape == "polaroid":
        _shape(group, "rounded", x, y, width, height, {"fill": "#fffefa", "stroke": theme["frame"], "stroke-width": 1})
        ix, iy, iw, ih = x + 13, y + 13, width - 26, height - 56
        image_shape = "rounded"
        label_y = y + height - 18
    elif shape == "postcard":
        _shape(group, "postcard", x, y, width, height, {"fill": "#fffefa", "stroke": theme["frame"], "stroke-width": 2})
        ix, iy, iw, ih = x + 11, y + 11, width - 22, height - 36
        image_shape = "postcard"
        label_y = y + height - 10
    else:
        fill = theme["card1"] if sticker_index % 2 == 0 else theme["card2"]
        _shape(group, shape, x, y, width, height, {"fill": fill, "stroke": theme["frame"],
                                                   "stroke-width": 2 if theme_id in {"botanical", "vintage"} else 1})
        ix, iy, iw, ih = x + 12, y + 12, width - 24, height - 42
        image_shape = shape
        label_y = y + height + 18 if shape in {"diamond", "ellipse"} else y + height - 12
        if theme_id == "vintage" and shape == "ellipse":
            _shape(group, "ellipse", x + 6, y + 6, width - 12, height - 12,
                   {"fill": "none", "stroke": theme["frame"], "stroke-width": 1})
    clip_id = f"page{page_index}-sticker{sticker_index}-clip"
    clip = _node(defs, "clipPath", {"id": clip_id, "clipPathUnits": "objectBoundingBox"})
    _clip_shape(clip, image_shape)
    sticker = deepcopy(artwork[sticker_index])
    prefix = f"p{page_index}s{sticker_index}-"
    for element in sticker.iter():
        if element.get("id"):
            element.set("id", prefix + element.get("id"))
        for key, value in list(element.attrib.items()):
            element.set(key, re.sub(r"url\(\s*['\"]?#([^)'\"\s]+)['\"]?\s*\)",
                                    lambda match: f"url(#{prefix}{match[1]})", value))
    sticker.set("x", str(ix))
    sticker.set("y", str(iy))
    sticker.set("width", str(iw))
    sticker.set("height", str(ih))
    sticker.set("preserveAspectRatio", "xMidYMid meet" if image_shape == "postcard" else "xMidYMid slice")
    sticker.set("clip-path", f"url(#{clip_id})")
    group.append(sticker)
    label = entry["stickers"][sticker_index]["label"]
    while text_width(label, 13) > width - 24:
        label = label[:-2].rstrip("…") + "…"
    _node(group, "text", {"x": x + width / 2, "y": label_y, "font-family": "Arial, sans-serif",
                          "font-size": 13 if theme_id != "vintage" else 12, "fill": theme["muted"],
                          "text-anchor": "middle"}, label)


def page_svg(entry: dict, layout: dict, index: int, artwork: list[ET.Element]) -> str:
    theme = THEMES.get(entry.get("theme", "minimal"), THEMES["minimal"])
    theme_id = entry.get("theme", "minimal")
    root = ET.Element(f"{{{NS}}}svg", {"width": str(PAGE_W), "height": str(PAGE_H),
                                     "viewBox": f"0 0 {PAGE_W} {PAGE_H}"})
    _node(root, "title", text=f"{entry['title']} — page {index + 1}")
    _node(root, "rect", {"width": PAGE_W, "height": PAGE_H, "fill": theme["paper"]})
    frame = {"x": 28, "y": 28, "width": PAGE_W - 56, "height": PAGE_H - 56,
             "rx": 22 if theme_id == "cozy" else 8 if theme_id == "travel" else 3,
             "fill": "none", "stroke": theme["frame"],
             "stroke-width": 2 if theme_id in {"botanical", "celebration", "cozy"} else 1,
             "stroke-dasharray": "9 8" if theme_id == "travel" else "none"}
    _node(root, "rect", frame)
    if theme_id == "vintage":
        _node(root, "rect", {"x": 38, "y": 38, "width": PAGE_W - 76, "height": PAGE_H - 76,
                              "rx": 2, "fill": "none", "stroke": theme["frame"], "stroke-width": 1})
    if theme_id == "cozy":
        _node(root, "rect", {"x": 44, "y": 44, "width": PAGE_W - 88, "height": PAGE_H - 88,
                              "rx": 18, "fill": "none", "stroke": theme["accent"], "stroke-width": 1,
                              "stroke-dasharray": "2 9"})
    defs = _node(root, "defs")
    base = {"font-family": "Arial, sans-serif", "fill": theme["muted"]}
    _node(root, "text", {**base, "x": MARGIN, "y": 73, "font-size": 12,
                          "letter-spacing": 2}, "DEAR ME · LITTLE MOMENTS, LOVINGLY KEPT")
    if theme_id == "botanical":
        for x, flip in ((44, 1), (856, -1)):
            _node(root, "path", {"d": f"M{x} 116 Q{x + 10 * flip} 95 {x + 28 * flip} 91 Q{x + 24 * flip} 110 {x} 116",
                                  "fill": "none", "stroke": theme["frame"], "stroke-width": 2, "stroke-linecap": "round"})
            for dx, dy in ((8, 106), (15, 99), (22, 94)):
                _node(root, "ellipse", {"cx": x + dx * flip, "cy": dy, "rx": 4, "ry": 8,
                                         "transform": f"rotate({-38 * flip} {x + dx * flip} {dy})",
                                         "fill": theme["accent"]})
        _node(root, "text", {**base, "x": PAGE_W / 2, "y": 106, "font-size": 11,
                              "letter-spacing": 2, "text-anchor": "middle"}, "FIELD NOTES · NO. 01")
    elif theme_id == "celebration":
        _node(root, "path", {"d": "M275 83 Q450 99 625 83", "fill": "none", "stroke": theme["frame"], "stroke-width": 2})
        for x, color in ((300, "#d79672"), (360, "#d4b15f"), (420, "#8ea17e"), (480, "#d79672"), (540, "#d4b15f"), (600, "#8ea17e")):
            _node(root, "path", {"d": f"M{x} {89 if x in (300, 600) else 94} l18 2 -9 16 -9 -16z", "fill": color})
    elif theme_id == "travel":
        _node(root, "text", {**base, "x": PAGE_W - MARGIN, "y": 73, "font-size": 11,
                              "letter-spacing": 2, "text-anchor": "end"}, "POSTCARD · DEAR ME")
        _node(root, "rect", {"x": 754, "y": 91, "width": 70, "height": 38, "rx": 3, "fill": "none",
                              "stroke": theme["frame"], "stroke-width": 2, "stroke-dasharray": "3 3"})
        _node(root, "circle", {"cx": 789, "cy": 110, "r": 11, "fill": theme["accent"]})
        _node(root, "path", {"d": "M780 112 l9 -13 3 9 8 3 -20 1z", "fill": theme["muted"]})
        _node(root, "path", {"d": "M660 108 C684 92 706 124 730 108", "fill": "none", "stroke": theme["frame"],
                              "stroke-width": 2, "stroke-dasharray": "4 5"})
    elif theme_id == "cozy":
        _node(root, "circle", {"cx": 790, "cy": 96, "r": 19, "fill": theme["accent"]})
        _node(root, "path", {"d": "M782 97 C782 89 790 90 791 96 C796 89 804 93 800 100 L791 108Z", "fill": theme["muted"]})
    elif theme_id == "vintage":
        _node(root, "circle", {"cx": 792, "cy": 99, "r": 24, "fill": theme["paper"], "stroke": theme["frame"], "stroke-width": 2})
        _node(root, "circle", {"cx": 792, "cy": 99, "r": 19, "fill": "none", "stroke": theme["frame"], "stroke-width": 1})
        _node(root, "text", {**base, "x": 792, "y": 96, "font-size": 8, "text-anchor": "middle",
                              "letter-spacing": 1}, "DEAR")
        _node(root, "text", {**base, "x": 792, "y": 106, "font-size": 10, "text-anchor": "middle"}, "✿")
        for x, y, direction in ((48, 48, 1), (852, 48, -1), (48, 1138, 1), (852, 1138, -1)):
            _node(root, "path", {"d": f"M{x} {y + 28} V{y} H{x + 28 * direction}", "fill": "none",
                                  "stroke": theme["frame"], "stroke-width": 1.5})
    centered = theme_id in {"celebration", "cozy", "vintage"}
    title_x = PAGE_W / 2 if centered else MARGIN
    title_attrs = {"x": title_x, "font-family": "Georgia, serif", "font-size": 35 if theme_id in {"cozy", "vintage"} else 33,
                   "fill": theme["title"], "text-anchor": "middle" if centered else "start"}
    title_top = 154 if theme_id == "celebration" else 137
    if theme_id == "botanical":
        title_attrs["font-style"] = "italic"
    if theme_id == "celebration":
        title_attrs["font-weight"] = 600
    for i, line in enumerate(layout["title_lines"]):
        _node(root, "text", {**title_attrs, "y": title_top + 40 * i}, line)
    date_y = 148 + 40 * (len(layout["title_lines"]) - 1)
    formatted = date.fromisoformat(entry["date"]).strftime("%B %d, %Y")
    date_offset = 22 if theme_id == "celebration" else 9
    _node(root, "text", {**base, "x": title_x, "y": date_y + date_offset, "font-size": 13,
                          "text-anchor": "middle" if centered else "start", "letter-spacing": 0.4}, formatted)
    line_top = date_y + (27 if theme_id == "celebration" else 13)
    _node(root, "line", {"x1": MARGIN, "y1": line_top, "x2": PAGE_W - MARGIN,
                          "y2": date_y + (32 if theme_id == "celebration" else 20), "stroke": theme["accent"], "stroke-width": 1.5})
    for block in layout["blocks"]:
        if block["type"] == "text":
            for line_no, line in enumerate(block["lines"]):
                _node(root, "text", {"x": MARGIN, "y": block["y"] + 22 + line_no * LINE_HEIGHT,
                                      "font-family": "Arial, sans-serif", "font-size": 20, "fill": theme["text"]}, line)
            continue
        indices = block["indices"]
        placements = _sticker_placements(theme_id, len(indices), block["y"], block["height"])
        for sticker_index, placement in zip(indices, placements):
            _draw_sticker(root, defs, entry, artwork, sticker_index, index, theme, theme_id, placement)
    _node(root, "line", {"x1": MARGIN, "y1": 1138, "x2": PAGE_W - MARGIN, "y2": 1138, "stroke": theme["accent"]})
    _node(root, "text", {**base, "x": MARGIN, "y": 1164, "font-family": "Georgia, serif", "font-size": 15,
                          "fill": theme["title"]}, "dear me")
    _node(root, "text", {**base, "x": PAGE_W - MARGIN, "y": 1164, "font-size": 13,
                          "text-anchor": "end"}, f"{index + 1} / {entry['page_count']}")
    return ET.tostring(root, encoding="unicode")


async def create_entry(title: str, text: str, day: date, sticker_ids: list[str], theme_id: str = "minimal") -> dict:
    if not text.strip() and not sticker_ids:
        raise ValueError("Select at least one sticker or write a little text before adding an entry.")
    if theme_id not in THEMES:
        raise ValueError("Choose one of the available scrapbook styles.")
    sticker_ids = list(dict.fromkeys(sticker_ids))
    resolved = [resolve_sticker(identifier) for identifier in sticker_ids]
    artwork = [validate_svg(path.read_text()) for _, path in resolved]
    title = title.strip() or "A little memory"
    layouts = paginate(title, text.strip(), len(artwork), theme_id)
    entry_id = uuid4().hex
    base = f"/api/v1/scrapbook/entries/{entry_id}/files"
    entry = {
        "id": entry_id, "title": title, "text": text.strip(), "date": day.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(), "page_count": len(layouts),
        "sticker_count": len(resolved), "theme": theme_id, "theme_label": THEMES[theme_id]["label"],
        "stickers": [item for item, _ in resolved], "pages": [],
    }
    root = storage_root()
    with TemporaryDirectory(prefix=".building-", dir=root) as temp:
        folder = Path(temp) / "entry"
        folder.mkdir()
        for i, svg in enumerate(artwork):
            (folder / f"sticker-{i}.svg").write_text(ET.tostring(svg, encoding="unicode"))
        for i, layout in enumerate(layouts):
            name = f"page-{i + 1}"
            (folder / f"{name}.svg").write_text(page_svg(entry, layout, i, artwork))
            await render_svg(folder / f"{name}.svg", folder / f"{name}.png")
            entry["pages"].append({"number": i + 1, "svg_url": f"{base}/{name}.svg",
                                    "image_url": f"{base}/{name}.png", "layout": layout})
        entry["download_url"] = f"{base}/scrapbook.zip"
        (folder / "entry.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False))
        with ZipFile(folder / "scrapbook.zip", "w", ZIP_DEFLATED) as archive:
            for path in sorted(folder.glob("page-*.*")):
                archive.write(path, path.name)
            archive.writestr("entry.txt", f"{entry['title']}\n{entry['date']}\n\n{entry['text']}")
        # Publish the completed pages together.
        folder.replace(root / entry_id)
    return entry


def get_entry(entry_id: str) -> dict | None:
    if not re.fullmatch(ID_PATTERN, entry_id):
        return None
    try:
        entry = json.loads((storage_root() / entry_id / "entry.json").read_text())
    except (OSError, ValueError):
        return None
    entry.setdefault("theme", "minimal")
    entry.setdefault("theme_label", THEMES[entry["theme"]]["label"])
    return entry


def list_entries() -> list[dict]:
    result = []
    for path in storage_root().glob("*/entry.json"):
        entry = get_entry(path.parent.name)
        if entry:
            result.append({k: entry[k] for k in ("id", "title", "date", "created_at", "page_count", "sticker_count", "theme", "theme_label")}
                          | {"image_url": entry["pages"][0]["image_url"], "excerpt": entry["text"][:140]})
    return sorted(result, key=lambda entry: entry["created_at"], reverse=True)
