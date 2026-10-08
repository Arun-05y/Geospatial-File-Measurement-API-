"""FastAPI Application Entry Point for Geospatial File Measurement API."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import v1_router
from app.config import settings
from app.core.error_handlers import generic_exception_handler, gfm_exception_handler
from app.core.exceptions import GFMException

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
Production-grade Geospatial File Measurement API.
Accepts ESRI Shapefiles (.zip) and OGC KML (.kml) files, automatically handles geographic coordinates (e.g. EPSG:4326) via dynamic UTM projection and geodesic computations, and measures feature area and length.
    """,
    openapi_tags=[
        {"name": "Files", "description": "Upload, inspect, and retrieve feature measurements."},
        {"name": "Health", "description": "Service health checks."},
    ],
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Exception Handlers
app.add_exception_handler(GFMException, gfm_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API Router
app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

# Static Files and Interactive Web Dashboard
static_path = Path(__file__).resolve().parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_dashboard():
        """Serves the interactive Leaflet-powered measurement dashboard."""
        return FileResponse(static_path / "index.html")
