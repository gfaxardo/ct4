from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models using modern DeclarativeBase."""
    pass

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


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
