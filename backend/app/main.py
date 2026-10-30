from fastapi import FastAPI

from app.routers import auth, catalogs, documents


def create_app() -> FastAPI:
    app = FastAPI(title="docvault")
    app.include_router(auth.router)
    app.include_router(catalogs.router)
    app.include_router(documents.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
