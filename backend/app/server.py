"""FastAPI 앱 — 헬스 + (Task 16에서) VFS/게이트웨이/WS 확장."""
from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="JB Marker API")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
