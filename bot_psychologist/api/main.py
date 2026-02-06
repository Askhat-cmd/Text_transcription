# api/main.py
"""
FastAPI Application for Bot Psychologist API (Phase 5)

Главный файл приложения с middleware, настройками и запуском.
"""

import logging
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

from .routes import router

logger = logging.getLogger(__name__)

# ===== LOGGING =====

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)

# ===== STARTUP TIME =====
_startup_time: float = 0.0


# ===== APP INITIALIZATION =====

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения"""
    global _startup_time
    # Startup
    _startup_time = time.time()
    logger.info("🚀 Bot Psychologist API v0.5.0 starting...")
    logger.info("✅ All modules loaded")
    yield
    # Shutdown
    logger.info("🛑 Bot Psychologist API shutting down...")


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
async def log_requests(request: Request, call_next):
    """Логировать все запросы"""
    start_time = time.time()
    
    # Получить API ключ (скрыть для логов)
    api_key = request.headers.get("X-API-Key", "none")
    api_key_masked = api_key[:10] + "..." if api_key != "none" and len(api_key) > 10 else api_key
    
    logger.info(f"→ {request.method} {request.url.path} (key: {api_key_masked})")
    
    try:
        response = await call_next(request)
        
        elapsed_time = time.time() - start_time
        logger.info(f"← {response.status_code} {request.url.path} ({elapsed_time:.2f}s)")
        
        return response
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
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


