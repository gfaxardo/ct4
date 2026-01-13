"""
Materialized View existence cache.

Caches the existence check of materialized views to avoid
repeated database queries on every API request.
"""
import logging
import time
from typing import Dict, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Cache: {mv_name: (exists: bool, timestamp: float)}
_mv_cache: Dict[str, Tuple[bool, float]] = {}

# Cache TTL in seconds (5 minutes)
MV_CACHE_TTL = 300


def mv_exists(db: Session, schema: str, mv_name: str, use_cache: bool = True) -> bool:
    """
    Check if a materialized view exists, with caching.
    
    Args:
        db: Database session
        schema: Schema name (e.g., 'ops')
        mv_name: Materialized view name
        use_cache: Whether to use the cache (default: True)
        
    Returns:
        True if the materialized view exists, False otherwise
    """
    cache_key = f"{schema}.{mv_name}"
    now = time.time()
    
    # Check cache first
    if use_cache and cache_key in _mv_cache:
        exists, cached_at = _mv_cache[cache_key]
        if now - cached_at < MV_CACHE_TTL:
            return exists
    
    # Query database
    try:
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_matviews 
                WHERE schemaname = :schema 
                AND matviewname = :mv_name
            )
        """), {"schema": schema, "mv_name": mv_name})
        exists = result.scalar() or False
        
        # Update cache
        _mv_cache[cache_key] = (exists, now)
        logger.debug(f"MV cache updated: {cache_key} = {exists}")
        
        return exists
    except Exception as e:
        logger.warning(f"Error checking MV existence for {cache_key}: {e}")
        # If cache has stale data, use it
        if cache_key in _mv_cache:
            return _mv_cache[cache_key][0]
        return False


def get_best_view(
    db: Session, 
    schema: str, 
    mv_candidates: list[str], 
    fallback_view: str
) -> str:
    """
    Get the best available view from a list of candidates.
    
    Checks materialized views in order and returns the first one that exists,
    or falls back to a regular view.
    
    Args:
        db: Database session
        schema: Schema name
        mv_candidates: List of MV names to check (in priority order)
        fallback_view: Regular view to use if no MVs exist
        
    Returns:
        Full view name (schema.view_name) of the best available view
    """
    for mv_name in mv_candidates:
        if mv_exists(db, schema, mv_name):
            logger.info(f"Using materialized view: {schema}.{mv_name}")
            return f"{schema}.{mv_name}"
    
    logger.info(f"No MVs found, using fallback view: {fallback_view}")
    return fallback_view


def clear_cache() -> None:
    """Clear the MV existence cache."""
    global _mv_cache
    _mv_cache.clear()
    logger.info("MV cache cleared")


def get_cache_stats() -> dict:
    """Get cache statistics."""
    now = time.time()
    total = len(_mv_cache)
    valid = sum(1 for _, (_, ts) in _mv_cache.items() if now - ts < MV_CACHE_TTL)
    
    return {
        "total_entries": total,
        "valid_entries": valid,
        "stale_entries": total - valid,
        "ttl_seconds": MV_CACHE_TTL
    }
