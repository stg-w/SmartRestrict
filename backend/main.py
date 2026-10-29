import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from backend.config import settings
from backend.database import init_db_pool, close_db_pool, check_db_health
from backend.routers import products, metadata, evaluate, alternatives, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smartrestrict.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Oracle Connection Pool
    logger.info("Initializing SmartRestrict backend...")
    init_db_pool()
    yield
    # Shutdown: Cleanly close pool
    logger.info("Shutting down SmartRestrict backend...")
    close_db_pool()

app = FastAPI(
    title="SmartRestrict API",
    description=(
        "Indian packaged-food nutrition, allergen, and dietary-restriction analysis platform. "
        "Powered by Oracle Database Free 26ai."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(products.router)
app.include_router(alternatives.router)
app.include_router(metadata.router)
app.include_router(evaluate.router)
app.include_router(users.router)

@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint providing Oracle database connection status and metrics."""
    return check_db_health()

# Mount frontend files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/catalogue", include_in_schema=False)
    def catalogue_page():
        return FileResponse(FRONTEND_DIR / "catalogue.html")

    @app.get("/product-detail", include_in_schema=False)
    def detail_page():
        return FileResponse(FRONTEND_DIR / "product-detail.html")

    @app.get("/evaluate", include_in_schema=False)
    def evaluate_page():
        return FileResponse(FRONTEND_DIR / "evaluate.html")

    @app.get("/profile", include_in_schema=False)
    def profile_page():
        return FileResponse(FRONTEND_DIR / "profile.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True
    )
