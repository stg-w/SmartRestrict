import logging
from contextlib import contextmanager
from typing import Generator, Any, Optional
import oracledb
from backend.config import settings

logger = logging.getLogger("smartrestrict.database")

_pool: Optional[oracledb.ConnectionPool] = None

def init_db_pool() -> Optional[oracledb.ConnectionPool]:
    """Initialize Oracle Connection Pool in thin mode."""
    global _pool
    if _pool is not None:
        return _pool

    if not settings.DB_PASSWORD:
        logger.warning("DB_PASSWORD is not set. Database operations will fail.")
        return None

    try:
        logger.info(
            f"Creating Oracle pool -> Host: {settings.DB_HOST}:{settings.DB_PORT}, "
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
            increment=1
        )
        logger.info("Oracle connection pool initialized successfully.")
        return _pool
    except oracledb.DatabaseError as e:
        error, = e.args
        logger.error(f"Oracle Pool initialization failed: {error.message} (Code: {error.code})")
        return None
    except Exception as e:
        logger.error(f"Unexpected error initializing Oracle pool: {e}")
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
        raise ConnectionError("Oracle connection pool is unavailable. Verify database host, port, and credentials.")

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
                res = cursor.fetchone()
                cursor.execute("SELECT COUNT(*) FROM PRODUCTS")
                prod_count = cursor.fetchone()[0]
                return {
                    "status": "healthy",
                    "oracle_version": conn.version,
                    "products_count": prod_count,
                    "connected_host": settings.DB_HOST,
                    "connected_service": settings.DB_SERVICE_NAME
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "target_host": settings.DB_HOST,
            "target_service": settings.DB_SERVICE_NAME
        }
