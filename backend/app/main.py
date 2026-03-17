import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, v1
from app.core.config import settings
from app.services.auto_processor import start_scheduler, stop_scheduler

def _cors_origins_list() -> list[str]:
    o = (settings.cors_origins or "").strip()
    if not o or o == "*":
        return ["*"]
    origins = [x.strip() for x in o.split(",") if x.strip()]
    # En local el frontend suele ir en localhost:3000; permitirlo siempre para desarrollo.
    if "http://localhost:3000" not in origins:
        origins.append("http://localhost:3000")
    return origins

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger()
logger.handlers = [handler]
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager para iniciar/detener servicios."""
    # Startup
    logger.info("Iniciando servicios de background...")
    start_scheduler()
    yield
    # Shutdown
    logger.info("Deteniendo servicios de background...")
    stop_scheduler()


app = FastAPI(
    title="CT4 Identity Canonical System",
    description="Sistema de Identidad Canónica - Fase 1",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,  # Cache preflight 24h
)

app.include_router(health.router)
app.include_router(v1.router, prefix="/api/v1")
