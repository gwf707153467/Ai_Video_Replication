from fastapi import APIRouter

from app.api.v1.routes import (
    assets,
    blueprint_routes,
    bridges,
    compile_routes,
    exports,
    projects,
    runtime_terminal,
    sequences,
    spus,
    studio,
    storage,
    vbus,
)

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(sequences.router, prefix="/sequences", tags=["sequences"])
api_router.include_router(spus.router, prefix="/spus", tags=["spus"])
api_router.include_router(vbus.router, prefix="/vbus", tags=["vbus"])
api_router.include_router(bridges.router, prefix="/bridges", tags=["bridges"])
api_router.include_router(compile_routes.router, prefix="/compile", tags=["compile"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(studio.router, prefix="/studio", tags=["studio"])
api_router.include_router(storage.router, prefix="/storage", tags=["storage"])
api_router.include_router(runtime_terminal.router, prefix="/runtime/terminal", tags=["runtime-terminal"])
api_router.include_router(blueprint_routes.router, prefix="/blueprints", tags=["blueprints"])
