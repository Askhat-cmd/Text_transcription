# api/main.py
"""
FastAPI Application for Bot Psychologist API (Phase 5)

Главный файл приложения с middleware, настройками и запуском.
"""

import asyncio
import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

# Добавить путь к bot_agent
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging_config import get_logger, setup_logging
from .routes import router
from .dependencies import set_preloaded_components

from bot_agent.config import config
from bot_agent.data_loader import data_loader
from bot_agent.graph_client import graph_client
from bot_agent.retriever import get_retriever
from bot_agent.semantic_memory import SemanticMemory

# ===== LOGGING =====
setup_logging()
logger = get_logger(__name__)

# ===== STARTUP TIME =====
_startup_time: float = 0.0


# ===== APP INITIALIZATION =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения"""
    global _startup_time
    # Startup
    _startup_time = time.time()
    logger.info("API server starting")
    logger.info("Version: %s", app.version)
    logger.info("Docs: http://localhost:8000/api/docs")

    if config.WARMUP_ON_START:
        logger.info("[WARMUP] starting warm preload")
        retriever = get_retriever()
        tasks = [
            ("data_loader", asyncio.to_thread(data_loader.load_all_data)),
            ("semantic_memory", asyncio.to_thread(lambda: SemanticMemory(user_id="__warmup__").ensure_model_loaded())),
            ("graph_client", asyncio.to_thread(graph_client.load_graphs_from_all_documents)),
            ("retriever", asyncio.to_thread(retriever.build_index)),
        ]
        results = await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)
        for (label, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.warning("[WARMUP] %s failed: %s", label, result)
        set_preloaded_components(
            data_loader=data_loader,
            graph_client=graph_client,
            retriever=retriever,
        )
        logger.info("[WARMUP] completed")

    yield
    # Shutdown
    uptime = time.time() - _startup_time if _startup_time else 0.0
    logger.info("API server shutting down | uptime=%.2fs", uptime)


app = FastAPI(
    title="Bot Psychologist API",
    description="""
# Bot Psychologist API

REST API для взаимодействия с Bot Agent (Phases 1-4).

## Возможности

- 🧠 **Phase 1:** Базовый QA (TF-IDF + LLM)
- 📊 **Phase 2:** SAG-aware QA (адаптация по уровню)
- 🔗 **Phase 3:** Graph-powered QA (Knowledge Graph)
- 🎯 **Phase 4:** Adaptive QA (состояние + память + пути)

## Аутентификация

Все endpoints (кроме health check) требуют API ключ в заголовке `X-API-Key`.

## Rate Limiting

Лимит запросов зависит от типа API ключа (100-1000 req/min).
    """,
    version="0.5.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# ===== MIDDLEWARE =====

# CORS для веб-интеграции
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "*"  # TODO: в production ограничить
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trust host
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
)


# Middleware для логирования
@app.middleware("http")
async def add_latency_header(request: Request, call_next):
    """Add X-Response-Time-Ms header to each response."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логировать все запросы"""
    start_ts = time.time()
    
    # Получить API ключ (скрыть для логов)
    api_key = request.headers.get("X-API-Key", "none")
    api_key_masked = api_key[:10] + "..." if api_key != "none" and len(api_key) > 10 else api_key
    
    logger.info("-> %s %s (key: %s)", request.method, request.url.path, api_key_masked)
    
    try:
        response = await call_next(request)
        
        elapsed_time = time.time() - start_ts
        logger.info("<- %s %s | status=%s | %.3fs", request.method, request.url.path, response.status_code, elapsed_time)
        
        return response
    
    except Exception as e:
        elapsed_time = time.time() - start_ts
        logger.error(
            "❌ Unhandled API error on %s %s after %.3fs: %s",
            request.method,
            request.url.path,
            elapsed_time,
            e,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "detail": "Internal Server Error"
            }
        )


# ===== ROUTERS =====

app.include_router(router)


# ===== CUSTOM OPENAPI =====

def custom_openapi():
    """Кастомная OpenAPI схема"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Bot Psychologist API",
        version="0.5.0",
        description="REST API для взаимодействия с Bot Agent (Phase 5)",
        routes=app.routes,
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ===== ROOT ENDPOINTS =====

@app.get("/", tags=["root"])
async def root():
    """Корневой endpoint"""
    return {
        "name": "Bot Psychologist API",
        "version": "0.5.0",
        "docs": "/api/docs",
        "status": "online"
    }


@app.get("/api/v1/info", tags=["info"])
async def api_info():
    """Информация об API"""
    return {
        "name": "Bot Psychologist API",
        "version": "0.5.0",
        "phases": {
            "phase_1": "Basic QA (TF-IDF + LLM)",
            "phase_2": "SAG-aware QA (User Level Adaptation)",
            "phase_3": "Graph-powered QA (Knowledge Graph + Semantic)",
            "phase_4": "Adaptive QA (State + Memory + Paths)",
            "phase_5": "REST API (FastAPI)"
        },
        "endpoints": {
            "basic": "/api/v1/questions/basic",
            "sag_aware": "/api/v1/questions/sag-aware",
            "graph_powered": "/api/v1/questions/graph-powered",
            "adaptive": "/api/v1/questions/adaptive",
            "history": "/api/v1/users/{user_id}/history",
            "feedback": "/api/v1/feedback",
            "stats": "/api/v1/stats"
        },
        "docs": "/api/docs"
    }


# ===== RUN =====

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


