import logging
import time
from contextlib import contextmanager
from typing import Generator, Any, Optional
import oracledb
from backend.config import settings

logger = logging.getLogger("smartrestrict.database")

_pool: Optional[oracledb.ConnectionPool] = None

def init_db_pool(max_retries: int = 3, retry_delay: float = 2.0) -> Optional[oracledb.ConnectionPool]:
    """Initialize Oracle Connection Pool in thin mode with retry logic."""
    global _pool
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")
    if retry_delay < 0:
        raise ValueError("retry_delay cannot be negative")
    if _pool is not None:
        return _pool

    if not settings.DB_PASSWORD:
        logger.warning("DB_PASSWORD is not set. Database operations will fail.")
        return None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Creating Oracle pool (attempt {attempt}/{max_retries}) -> "
                f"Host: {settings.DB_HOST}:{settings.DB_PORT}, "
                f"Service: {settings.DB_SERVICE_NAME}, User: {settings.DB_USER}"
            )
            _pool = oracledb.create_pool(
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                service_name=settings.DB_SERVICE_NAME,
                min=1,
                max=10,
                increment=1,
                timeout=30,
                wait_timeout=5000,
            )
            logger.info("Oracle connection pool initialized successfully.")
            return _pool
        except oracledb.DatabaseError as e:
            error = e.args[0] if e.args else e
            logger.error(
                f"Oracle Pool init failed (attempt {attempt}): "
                f"{getattr(error, 'message', str(error))} "
                f"(Code: {getattr(error, 'code', 'unknown')})"
            )
            if attempt < max_retries:
                wait = retry_delay * (2 ** (attempt - 1))  # exponential backoff
                logger.info(f"Retrying in {wait:.1f}s...")
                time.sleep(wait)
        except Exception as e:
            logger.error(f"Unexpected error initializing Oracle pool: {e}")
            break

    logger.error("All Oracle pool initialization attempts failed.")
    return None

def close_db_pool():
    """Close all pooled connections gracefully."""
    global _pool
    if _pool is not None:
        try:
            _pool.close(force=False)
            logger.info("Oracle connection pool closed.")
        except Exception as e:
            logger.error(f"Error closing Oracle pool: {e}")
        finally:
            _pool = None

@contextmanager
def get_db_connection() -> Generator[oracledb.Connection, None, None]:
    """Context manager for acquiring and releasing a pooled connection."""
    global _pool
    if _pool is None:
        _pool = init_db_pool()

    if _pool is None:
        raise ConnectionError(
            "Oracle connection pool is unavailable. "
            "Verify DB_HOST, DB_PORT, and credentials in your .env file."
        )

    try:
        conn = _pool.acquire()
    except oracledb.DatabaseError as e:
        error = e.args[0] if e.args else e
        # DPY-6005 / ORA-12570: session timeout — try once more with a fresh pool
        logger.warning(
            "Pool acquire failed (%s), attempting pool reinit...",
            getattr(error, "message", str(error)),
        )
        close_db_pool()
        _pool = init_db_pool(max_retries=1)
        if _pool is None:
            raise ConnectionError("Could not reacquire a database connection. Database may be unreachable.")
        conn = _pool.acquire()

    try:
        yield conn
    finally:
        _pool.release(conn)

def rows_to_dicts(cursor: oracledb.Cursor) -> list[dict[str, Any]]:
    """Convert cursor results to a list of dicts with lowercase column keys."""
    if cursor.description is None:
        return []
    columns = [col[0].lower() for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def row_to_dict(cursor: oracledb.Cursor, row: Optional[tuple]) -> Optional[dict[str, Any]]:
    """Convert a single cursor row to a dict with lowercase column keys."""
    if row is None or cursor.description is None:
        return None
    columns = [col[0].lower() for col in cursor.description]
    return dict(zip(columns, row))

def check_db_health() -> dict[str, Any]:
    """Check database connectivity and return basic status."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM DUAL")
                cursor.fetchone()
                cursor.execute("SELECT COUNT(*) FROM PRODUCTS")
                prod_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM BRANDS")
                brand_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM CATEGORIES")
                cat_count = cursor.fetchone()[0]
                return {
                    "status": "healthy",
                    "oracle_version": conn.version,
                    "products_count": prod_count,
                    "brands_count": brand_count,
                    "categories_count": cat_count,
                    "connected_host": settings.DB_HOST,
                    "connected_service": settings.DB_SERVICE_NAME,
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "target_host": settings.DB_HOST,
            "target_service": settings.DB_SERVICE_NAME,
        }
