"""Photo → Bob SVG illustration → validated vector border → transparent PNG."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
import json
from pathlib import Path
import shutil

from app.core.config import PROJECT_ROOT
from app.models.schemas import ExtractedObject, ExtractionResult
from app.services.bob_client import BobError, run_bob
from app.services.svg_stickers import SVGError, build_sticker

STYLES = {
    "paper": "warm handmade cut-paper illustration, matte colors, rounded organic shapes, subtle shading",
    "soft": "soft illustrated vector shapes, restrained gradients, fine warm outlines and thoughtful highlights",
    "ink": "expressive ink illustration, clean flowing linework, limited warm colors, simplified details",
}
STYLE_ALIASES = {"collage": "paper", "vintage": "paper", "watercolor": "soft", "lineart": "ink"}


async def render_svg(source: Path, destination: Path) -> None:
    node = shutil.which("node")
    if not node:
        raise BobError("Node.js is required to render the sticker preview. Run ./start-local.sh.")
    process = await asyncio.create_subprocess_exec(
        node, str(PROJECT_ROOT / "tools/render-svg.cjs"), str(source), str(destination),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(process.communicate(), 30)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise SVGError("Rendering timed out. Try a simpler subject.") from None
    if process.returncode or not destination.is_file():
        raise SVGError("Try generating the sticker again with a simpler subject.")


async def extract_objects_from_image(
    image_path: str, style: str = "paper", *, subject: str = "", instructions: str = "",
    count: int = 1, phase: Callable[[str], None] | None = None,
) -> ExtractionResult:
    style = STYLE_ALIASES.get(style, style)
    if style not in STYLES:
        raise ValueError("Choose paper, soft, or ink illustration.")
    reference = Path(image_path).resolve()
    folder = reference.parent
    request = json.dumps({"subject": subject, "instructions": instructions, "max_stickers": count}, ensure_ascii=False)
    prompt = f"""Create scrapbook illustrations from the image in @{reference.name}.
Use the read tool to view this reference and follow these artwork preferences:
{request}

Illustrate the requested subject, or choose the most distinctive visible subject. Create up to {count} separate illustrations of objects in the photo. Preserve their identifying colors, proportions and details. A head portrait includes the face, ears and whiskers.
Visual style: {STYLES[style]}.
Keep the shapes readable at sticker size. Connect the main silhouette, overlap layered shapes, and attach small decorations to their subject. Clip patterns and decorations to the shape they belong to.
Create colored subject artwork on a transparent canvas. The application adds the white border afterward. Fit the subject within x=45..595,y=45..595 on a 640x640 canvas, preserving its aspect ratio.
SVG format: xmlns="http://www.w3.org/2000/svg", width="640", height="640", viewBox="0 0 640 640". Place definitions in <defs> and every visible shape in one top-level <g id="artwork">. Supported elements: svg, title, desc, defs, g, path, circle, ellipse, rect, polygon, polyline, line, linearGradient, radialGradient, stop, clipPath. Use local gradient and clip-path references and keep each SVG below 10000 characters.
Deliver complete SVG markup in this JSON response:
{{"objects":[{{"label":"short subject name","description":"one sentence describing the illustration","svg":"complete SVG markup"}}]}}"""
    if phase:
        phase("generating")
    payload, usage = await run_bob(prompt, folder)
    objects = payload.get("objects")
    if not isinstance(objects, list) or not objects or len(objects) > count:
        raise BobError("Try generating again with a clearer subject.")
    if phase:
        phase("finishing")
    output: list[ExtractedObject] = []
    for index, item in enumerate(objects):
        if not isinstance(item, dict):
            raise BobError("Bob returned an invalid sticker object.")
        raw, final = build_sticker(item.get("svg", ""))
        (folder / f"artwork-{index}.svg").write_text(raw)
        sticker_path = folder / f"sticker-{index}.svg"
        sticker_path.write_text(final)
        await render_svg(sticker_path, folder / f"sticker-{index}.png")
        base = f"/api/v1/studio/jobs/{folder.name}/files"
        output.append(ExtractedObject(
            label=str(item.get("label", "Sticker"))[:80], style=style,
            description=str(item.get("description", "Bob-generated vector illustration"))[:400],
            image_url=f"{base}/sticker-{index}.png", svg_url=f"{base}/sticker-{index}.svg",
            artwork_url=f"{base}/artwork-{index}.svg",
        ))
    return ExtractionResult(
        source_image_url=f"/api/v1/studio/jobs/{folder.name}/files/original.png", objects=output, usage=usage,
    )
