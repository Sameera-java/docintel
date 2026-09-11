"""
Application entrypoint.
Serves the REST API (under /api/v1) AND the HTML frontend (Jinja2 templates +
static files) from a single FastAPI app, so only ONE service needs deploying.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import documents
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
settings = get_settings()

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root (backend's parent)
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix=settings.API_PREFIX, tags=["documents"])

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))


@app.on_event("startup")
def on_startup():
    logger.info("Starting %s", settings.APP_NAME)
    init_db()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
    )


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/document/{document_name}")
def document_result_page(request: Request, document_name: str):
    return templates.TemplateResponse(
        "document_result.html", {"request": request, "document_name": document_name}
    )
