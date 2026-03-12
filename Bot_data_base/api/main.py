from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import os

from api.routes.youtube import router as youtube_router
from api.routes.books import router as books_router
from api.routes.registry import router as registry_router
from api.routes.status import router as status_router

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(env_path, override=False)

_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
root_logger = logging.getLogger()
root_logger.setLevel(_log_level)
for handler in root_logger.handlers:
    handler.setLevel(_log_level)

app = FastAPI(title="Bot_data_base Admin API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(youtube_router, prefix="/api/ingest")
app.include_router(books_router, prefix="/api/ingest")
app.include_router(registry_router, prefix="/api/registry")
app.include_router(status_router, prefix="/api/status")

# Static
app.mount("/static", StaticFiles(directory="web_ui/static", check_dir=False), name="static")

templates = Jinja2Templates(directory="web_ui")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/youtube")
async def youtube_page(request: Request):
    return templates.TemplateResponse("youtube.html", {"request": request})


@app.get("/books")
async def books_page(request: Request):
    return templates.TemplateResponse("books.html", {"request": request})


@app.get("/registry")
async def registry_page(request: Request):
    return templates.TemplateResponse("registry.html", {"request": request})
