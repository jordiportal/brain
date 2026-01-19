"""
Browser - Servicio de navegación web usando Playwright
"""

from .service import BrowserService, browser_service
from .router import router as browser_router

__all__ = [
    "BrowserService",
    "browser_service",
    "browser_router"
]
