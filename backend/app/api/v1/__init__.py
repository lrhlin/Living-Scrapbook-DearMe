from fastapi import APIRouter

from app.api.v1 import entries, memory_graph, aesthetic, extract, chapters, studio, scrapbook

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(entries.router)
api_router.include_router(memory_graph.router)
api_router.include_router(aesthetic.router)
api_router.include_router(extract.router)
api_router.include_router(chapters.router)
api_router.include_router(studio.router)
api_router.include_router(scrapbook.router)
