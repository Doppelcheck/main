"""
FastAPI application setup for the Web Content Analysis Bookmarklet System.
"""
import webbrowser
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from pathlib import Path

from server.routes import bookmarklet_router, extract_router, retrieve_router, compare_router, config_router
from server.utils import config

# Get the root directory
ROOT_DIR = Path(__file__).parent.parent

# lifecycle handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup-Logik
    logger.info("Server is starting up...")
    logger.info(f"Configuration: {config.get_config()}")

    # Browser öffnen
    url = f"http://{config.get('host')}:{config.get('port')}"
    logger.info(f"Opening browser at {url}")
    webbrowser.open(url)

    yield  # Hier wird der Server gestartet

    # Shutdown-Logik
    logger.info("Server is shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        config: Application configuration dictionary

    Returns:
        Configured FastAPI application
    """

    # Create FastAPI app
    app = FastAPI(
        title="Web Content Analysis Bookmarklet",
        description="A system for analyzing web content with LLM assistance",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
    )

    # Set up static files
    static_dir = ROOT_DIR / "server" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    else:
        logger.warning(f"Static directory not found: {static_dir}")

    # Set up templates
    app.state.templates = Jinja2Templates(directory=ROOT_DIR / "server" / "templates")


    # Mount routers
    app.include_router(bookmarklet_router)
    app.include_router(extract_router)
    app.include_router(retrieve_router)
    app.include_router(compare_router)
    app.include_router(config_router)


    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "message": "Web Content Analysis Bookmarklet API",
            "docs": "/api/docs",
            "bookmarklet": "/bookmarklet"
        }

    return app