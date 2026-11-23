"""Validate generated vectors and derive borders from the real artwork geometry."""
from __future__ import annotations

from copy import deepcopy
import math
import re
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
SHAPES = {"path", "circle", "ellipse", "rect", "polygon", "polyline", "line"}
ALLOWED = SHAPES | {"svg", "title", "desc", "defs", "g", "linearGradient", "radialGradient", "stop", "clipPath"}
ATTRIBUTES = {
    "id", "viewBox", "width", "height", "x", "y", "x1", "y1", "x2", "y2",
    "cx", "cy", "r", "rx", "ry", "fx", "fy", "d", "points", "transform",
    "fill", "fill-rule", "fill-opacity", "stroke", "stroke-width", "stroke-linejoin",
    "stroke-linecap", "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset",
    "stroke-opacity", "opacity", "clip-path", "clip-rule", "clipPathUnits",
    "gradientUnits", "gradientTransform", "spreadMethod", "offset", "stop-color",
    "stop-opacity", "preserveAspectRatio", "vector-effect",
}


class SVGError(ValueError):
    pass


def validate_svg(svg: str) -> ET.Element:
    if not isinstance(svg, str) or len(svg.encode()) > 180_000:
        raise SVGError("The generated SVG is too large.")
    if re.search(r"<!DOCTYPE|<!ENTITY|<\?", svg, re.I):
        raise SVGError("The generated SVG contains unsupported document declarations.")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise SVGError("Bob returned an incomplete SVG. Please try again.") from exc
    if root.tag != f"{{{NS}}}svg":
        raise SVGError("Generate the illustration again in SVG format.")
    if len(list(root.iter())) > 2500:
        raise SVGError("The generated artwork has too many elements.")
    ids: set[str] = set()
    references: set[str] = set()
    for element in root.iter():
        if element.tag not in {f"{{{NS}}}{tag}" for tag in ALLOWED}:
            raise SVGError("The artwork includes unsupported elements.")
        style = element.attrib.pop("style", "")
        for declaration in style.split(";"):
            if declaration.strip():
                name, separator, value = declaration.partition(":")
                if not separator:
                    raise SVGError("The artwork contains an invalid style.")
                element.set(name.strip(), value.strip())
        for name, value in element.attrib.items():
            if name not in ATTRIBUTES or re.search(r"javascript:|data:|https?:|@import", value, re.I):
                raise SVGError("The artwork contains an unsupported attribute or external resource.")
            if name == "id":
                if value in ids or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", value):
                    raise SVGError("The artwork contains invalid or duplicate identifiers.")
                ids.add(value)
            for resource in re.findall(r"url\((.*?)\)", value):
                resource = resource.strip(" \"'")
                if not resource.startswith("#"):
                    raise SVGError("Use local SVG gradients and clipping paths.")
                references.add(resource[1:])
    if not references <= ids:
        raise SVGError("The artwork references missing gradients or clipping paths.")
    try:
        bounds = [float(x) for x in root.get("viewBox", "").replace(",", " ").split()]
        if len(bounds) != 4 or not all(math.isfinite(x) for x in bounds) or not (32 <= bounds[2] <= 4096 and 32 <= bounds[3] <= 4096):
            raise ValueError
    except ValueError:
        raise SVGError("The artwork has an invalid canvas size.") from None
    root.set("width", str(bounds[2]))
    root.set("height", str(bounds[3]))
    return root


def build_sticker(svg: str, border_width: float = 7) -> tuple[str, str]:
    root = validate_svg(svg)
    tag = lambda name: f"{{{NS}}}{name}"
    artwork = next((e for e in root if e.get("id") == "artwork"), None)
    visible = [e for e in root if e.tag not in {tag("title"), tag("desc"), tag("defs")}]
    if artwork is None or artwork.tag != tag("g") or visible != [artwork]:
        raise SVGError("Generate the sticker again with a single artwork group.")
    if not any(e.tag.rsplit("}", 1)[-1] in SHAPES for e in artwork.iter()):
        raise SVGError("Generate the sticker again with visible artwork shapes.")
    raw = ET.tostring(root, encoding="unicode")
    backing = deepcopy(artwork)

    def whiten(element: ET.Element, inherited: dict) -> None:
        paint = {**inherited, **{k: element.get(k) for k in ("fill", "stroke", "stroke-width") if k in element.attrib}}
        element.attrib.pop("id", None)
        element.set("opacity", "1")
        element.set("fill-opacity", "1")
        element.set("stroke-opacity", "1")
        if element.tag.rsplit("}", 1)[-1] in SHAPES:
            try:
                width = float(paint["stroke-width"].removesuffix("px")) if paint["stroke"] != "none" else 0
                if not math.isfinite(width) or width < 0 or width > 64:
                    raise ValueError
            except ValueError:
                raise SVGError("The artwork uses an unsupported outline width.") from None
            element.set("fill", "none" if paint["fill"] == "none" else "#fffdf7")
            element.set("stroke", "#fffdf7")
            element.set("stroke-width", str(2 * border_width + width))
            element.set("stroke-linejoin", "round")
            element.set("stroke-linecap", "round")
        for child in element:
            whiten(child, paint)

    whiten(backing, {"fill": root.get("fill", "#000"), "stroke": root.get("stroke", "none"), "stroke-width": root.get("stroke-width", "1")})
    backing.set("id", "dearme-sticker-border")
    root.insert(list(root).index(artwork), backing)
    final = ET.tostring(root, encoding="unicode")
    validate_svg(final)
    return raw, final
