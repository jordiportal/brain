"""
Browser Router - Endpoints para el servicio de navegador
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import structlog

from .service import browser_service

logger = structlog.get_logger()

router = APIRouter(prefix="/browser", tags=["Browser"])


# ===== Modelos de Request/Response =====

class NavigateRequest(BaseModel):
    """Request para navegar a una URL"""
    url: str
    session_id: Optional[str] = None


class ClickRequest(BaseModel):
    """Request para hacer clic"""
    selector: str
    session_id: Optional[str] = None


class TypeRequest(BaseModel):
    """Request para escribir texto"""
    selector: str
    text: str
    press_enter: bool = False
    session_id: Optional[str] = None


class ScreenshotRequest(BaseModel):
    """Request para captura de pantalla"""
    full_page: bool = False
    session_id: Optional[str] = None


# ===== Endpoints =====

@router.get("/status")
async def get_browser_status():
    """Obtener estado del servicio de navegador"""
    return browser_service.get_status()


@router.post("/initialize")
async def initialize_browser():
    """Inicializar el servicio de navegador"""
    success = await browser_service.initialize()
    
    if success:
        return {
            "initialized": True,
            **browser_service.get_status()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="No se pudo inicializar el navegador"
        )


@router.post("/navigate")
async def navigate_to_url(request: NavigateRequest):
    """Navegar a una URL"""
    result = await browser_service.navigate(
        url=request.url,
        session_id=request.session_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.post("/click")
async def click_element(request: ClickRequest):
    """Hacer clic en un elemento"""
    result = await browser_service.click(
        selector=request.selector,
        session_id=request.session_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.post("/type")
async def type_text(request: TypeRequest):
    """Escribir texto en un campo"""
    result = await browser_service.type_text(
        selector=request.selector,
        text=request.text,
        session_id=request.session_id,
        press_enter=request.press_enter
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.post("/screenshot")
async def take_screenshot(request: ScreenshotRequest):
    """Tomar captura de pantalla"""
    result = await browser_service.screenshot(
        session_id=request.session_id,
        full_page=request.full_page
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.get("/content")
async def get_page_content(session_id: Optional[str] = None, selector: str = "body"):
    """Obtener contenido de la página"""
    result = await browser_service.get_content(
        session_id=session_id,
        selector=selector
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.get("/elements")
async def get_page_elements(session_id: Optional[str] = None, limit: int = 50):
    """Obtener elementos interactivos de la página"""
    result = await browser_service.get_elements(
        session_id=session_id,
        limit=limit
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.delete("/session/{session_id}")
async def close_session(session_id: str):
    """Cerrar una sesión de navegador"""
    await browser_service.close_session(session_id)
    return {"closed": True, "session_id": session_id}
