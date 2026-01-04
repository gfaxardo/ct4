from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings

# Configurar engine con pool de conexiones robusto
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verifica conexiones antes de usarlas
    pool_recycle=3600,  # Recicla conexiones cada hora
    pool_size=10,  # Tamaño del pool
    max_overflow=20,  # Conexiones adicionales permitidas
    connect_args={
        "connect_timeout": 10,  # Timeout de conexión en segundos
        "options": "-c statement_timeout=30000"  # Timeout de statement en ms (30s)
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
