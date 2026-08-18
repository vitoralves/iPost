import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ipost.settings import get_settings
from ipost_api.deps import require_admin
from ipost_api.routes import public_router, router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="iPost", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=r"https://([a-z0-9-]+\.)?vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(public_router)
    app.include_router(router, dependencies=[Depends(require_admin)])

    @app.get("/")
    def root() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    uvicorn.run("ipost_api.main:app", host="0.0.0.0", port=8000, reload=True)
