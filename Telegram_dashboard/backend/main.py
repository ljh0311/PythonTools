from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_DIR, HOST, PORT
from backend.routes.agent import router as agent_router
from backend.routes.api import router as api_router
from backend.routes.auth import router as auth_router
from backend.routes.webhook import router as webhook_router


app = FastAPI(
    title="Telegram Dashboard API",
    description="Backend for Telegram bot integration and dashboard UI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(agent_router)
app.include_router(webhook_router)

frontend_path = Path(FRONTEND_DIR)
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/")
async def serve_dashboard():
    index = frontend_path / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Telegram Dashboard API is running. Frontend not found."}


@app.get("/login")
async def serve_login():
    page = frontend_path / "login.html"
    if page.exists():
        return FileResponse(page)
    return {"message": "Login page not found."}


@app.get("/feedback")
async def serve_feedback():
    page = frontend_path / "feedback.html"
    if page.exists():
        return FileResponse(page)
    return {"message": "Feedback page not found."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
