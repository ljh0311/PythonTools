"""Gemini Image Studio FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS, HOST, PORT, ensure_outputs_dir
from backend.routes.generate import router as generate_router

ensure_outputs_dir()

app = FastAPI(title="Gemini Image Studio", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate_router)


@app.get("/")
def root() -> dict:
    return {
        "name": "Gemini Image Studio",
        "docs": "/docs",
        "health": "/api/health",
    }


def run() -> None:
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=False,
    )


if __name__ == "__main__":
    run()
