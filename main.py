#!/usr/bin/env python3
"""
Main entry point for the Web Content Analysis Bookmarklet System.
This script initializes the web server and LLM service.
"""

import os
import sys
import webbrowser
import asyncio
from contextlib import asynccontextmanager
import subprocess

import spacy
import uvicorn
from loguru import logger

from server.app import create_app

# Import check_ollama from the llm service
from server.services.llm_ollama import check_ollama
from server.utils import config
import stanza


def setup_logging(debug: bool = False):
    """Configure logging with Loguru."""
    logger.remove()
    log_level = "DEBUG" if debug else "INFO"
    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    )

async def on_startup(host, port):
    """Function to be called when the server starts up."""
    bookmarklet_url = f"http://{host}:{port}/bookmarklet"
    logger.info(f"Opening browser to {bookmarklet_url}")
    webbrowser.open(bookmarklet_url)


@asynccontextmanager
async def lifespan(app):
    config = app.state.config
    if config.get("open_browser", True):
        asyncio.create_task(on_startup(config["host"], config["port"]))
    yield


def start_server():
    """Start the FastAPI server with the given configuration."""
    host = config.get("host")
    port = config.get("port")
    logger.info(f"Starting server at http://{host}:{port}")
    # logger.info(f"Bookmarklet available at http://{host}:{port}/bookmarklet")

    app = create_app()

    debug = config.get("debug", True)

    uvicorn.run(app, host=host, port=port, log_level="debug" if debug else "info")


def initialize() -> None:
    try:
        subprocess.run(["pip", "install", "--upgrade", "pip"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error upgrading pip: {e}")
        sys.exit(1)

    # stanza.download('multilingual')
    try:
        stanza.download("multilingual")
    except Exception as e:
        print(f"Error downloading stanza multilingual model: {e}")
        sys.exit(1)

    # Try to use playwright, install only if it fails
    try:
        subprocess.run(["playwright", "version"], check=True, capture_output=True)
        logger.info("Playwright already installed")

    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info("Installing Playwright...")
        # os.system("sudo apt-get install libxcursor1 libxdamage1 libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0 libatk1.0-0 libcairo-gobject2 libcairo2 libgdk-pixbuf-2.0-0 libasound2 libdbus-glib-1-2")
        try:
            # os.system("playwright install-deps")
            os.system("playwright install")

        except Exception as e:
            print(
                f"Error installing playwright: {e}\n"
                f"Make sure to install the required dependencies:\n"
                f"  - either run `playwright install-deps` "
                f"  - or install individually:\n"
                f"    - libxcursor1"
                f"    - libxdamage1"
                f"    - libgtk-3-0"
                f"    - libpangocairo-1.0-0"
                f"    - libpango-1.0-0"
                f"    - libatk1.0-0"
                f"    - libcairo-gobject2"
                f"    - libcairo2"
                f"    - libgdk-pixbuf-2.0-0"
                f"    - libasound2"
                f"    - libdbus-glib-1-2"
            )

    try:
        _nlp = spacy.load("de_core_news_lg")
        print("de_core_news_lg is already installed!")

    except OSError:
        print("de_core_news_lg is not installed. Running 'python -m spacy download de_core_news_lg'")
        os.system("python -m spacy download de_core_news_lg")

    configuration = config.get_config()
    setup_logging(configuration["debug"])
    if not check_ollama(configuration["model"], configuration["ollama_host"]):
        logger.error("Failed to ensure Ollama is running. Exiting.")
        sys.exit(1)

def main():
    initialize()
    start_server()


if __name__ == "__main__":
    main()