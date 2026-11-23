from __future__ import annotations

import re
import shutil
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.core.config import PROJECT_ROOT, settings
from app.services.bob_client import BobError, cli_path
from app.services.object_extractor import STYLES
from app.services import studio_jobs

router = APIRouter(prefix="/studio", tags=["studio"])
EXAMPLES = {
    "cat": {"title": "A familiar face", "subject": "Cat head only", "credit": "Donald Teel / Unsplash", "source": "https://unsplash.com/photos/a-close-up-of-a-tabby-cats-face-TgY5w9lpqDE", "extension": "jpg"},
    "tree": {"title": "A little holiday magic", "subject": "Christmas tree", "credit": "BrunoZ / PurePNG", "source": "https://purepng.com/photo/28503/nature-christmas-tree-traditional", "extension": "png"},
    "school": {"title": "Somewhere that matters", "subject": "School building", "credit": "South Seneca Central School District", "source": "https://www.southseneca.org/o/elementary-school/article/897982", "extension": "jpg"},
}


@router.get("/status")
def status() -> dict:
    return {
        "configured": bool(settings.read_bob_key()), "cli_available": bool(cli_path()),
        "renderer_available": bool(shutil.which("node") and (PROJECT_ROOT / "tools/node_modules/@resvg/resvg-js").is_dir()),
        "max_bobcoins": settings.bob_max_cost, "max_upload_mb": settings.max_upload_size_mb,
        "provider": "IBM Bob", "output": "SVG illustration with a locally generated border",
    }


@router.get("/examples")
def examples() -> list[dict]:
    return [{"slug": slug, **item, "original_url": f"/api/v1/studio/examples/{slug}/original",
             "sticker_url": f"/api/v1/studio/examples/{slug}/png", "svg_url": f"/api/v1/studio/examples/{slug}/svg"}
            for slug, item in EXAMPLES.items()]


@router.get("/examples/{slug}/{kind}")
def example_file(slug: str, kind: str) -> FileResponse:
    if slug not in EXAMPLES or kind not in {"original", "png", "svg"}:
        raise HTTPException(404, "Example not found")
    suffix = f"original.{EXAMPLES[slug]['extension']}" if kind == "original" else f"sticker.{kind}"
    path = PROJECT_ROOT / "artifacts/bob-sticker-examples" / f"{slug}-{suffix}"
    if not path.is_file():
        raise HTTPException(404, "Choose another example or upload a photo.")
    return FileResponse(path, headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox"})


@router.post("/jobs", status_code=202)
async def create(
    file: UploadFile = File(...), style: str = Form("paper"), subject: str = Form(""),
    instructions: str = Form(""), count: int = Form(1),
) -> dict:
    if style not in STYLES or not 1 <= count <= 3 or len(subject) > 120 or len(instructions) > 600:
        raise HTTPException(400, "Choose a style, one to three stickers, and shorter subject instructions.")
    ready = status()
    if not all(ready[k] for k in ("configured", "cli_available", "renderer_available")):
        raise HTTPException(503, "Add bobkey.txt and run ./start-local.sh to set up Bob.")
    limit = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, f"Choose a photo smaller than {settings.max_upload_size_mb} MB.")
    try:
        return await studio_jobs.create_job(content, style=style, subject=subject.strip(), instructions=instructions.strip(), count=count)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except BobError as exc:
        raise HTTPException(429, str(exc)) from None


@router.get("/jobs")
def library() -> list[dict]:
    return studio_jobs.list_jobs()


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise HTTPException(404, "Generation not found")
    job = studio_jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "Generation not found")
    return job


@router.get("/jobs/{job_id}/files/{filename}")
def job_file(job_id: str, filename: str, download: bool = False) -> FileResponse:
    get_job(job_id)
    if filename != "original.png" and not re.fullmatch(r"(?:sticker|artwork)-[0-2]\.(?:png|svg)", filename):
        raise HTTPException(404, "Sticker file not found")
    path = studio_jobs.job_root() / job_id / filename
    if not path.is_file():
        raise HTTPException(404, "Sticker file not found")
    return FileResponse(path, filename=filename if download else None, headers={
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
        "X-Content-Type-Options": "nosniff",
    })
