"""
Browser Service - Servicio de navegación web usando Playwright

Proporciona herramientas de navegación web para los agentes.
Soporta:
- Navegador local (headless o headed)
- Navegador remoto via CDP (Chrome DevTools Protocol)
"""

import asyncio
import base64
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import structlog
import httpx

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None
    BrowserContext = None

logger = structlog.get_logger()

# Configuración
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
BROWSER_VNC_HOST = os.getenv("BROWSER_VNC_HOST", "browser")  # Host del servicio VNC
BROWSER_CDP_PORT = os.getenv("BROWSER_CDP_PORT", "9222")  # Puerto CDP del browser-service


@dataclass
class BrowserSession:
    """Sesión de navegador"""
    id: str
    browser: Optional[Any] = None
    context: Optional[Any] = None
    page: Optional[Any] = None
    is_active: bool = False


class BrowserService:
    """
    Servicio de navegación web usando Playwright.
    
    Proporciona métodos para:
    - Navegar a URLs
    - Hacer clic en elementos
    - Escribir texto
    - Tomar capturas de pantalla
    - Obtener contenido de la página
    
    Se conecta al navegador del browser-service via CDP para que
    las acciones se vean en el visor VNC.
    """
    
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._sessions: Dict[str, BrowserSession] = {}
        self._default_session_id = "default"
        self._lock = asyncio.Lock()
        self._headless = BROWSER_HEADLESS
        self._is_remote = False
    
    async def _get_remote_cdp_url(self) -> Optional[str]:
        """Obtener la URL del WebSocket CDP del navegador remoto"""
        if not BROWSER_VNC_HOST:
            return None
        
        # Usamos el puerto 9223 que es el proxy socat que acepta conexiones externas
        cdp_proxy_port = "9223"
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Chrome requiere que el Host header sea localhost
                response = await client.get(
                    f"http://{BROWSER_VNC_HOST}:{cdp_proxy_port}/json/version",
                    headers={"Host": "localhost"}
                )
                if response.status_code == 200:
                    data = response.json()
                    ws_url = data.get("webSocketDebuggerUrl", "")
                    # Reemplazar localhost con el host:puerto del proxy
                    ws_url = ws_url.replace("ws://localhost/", f"ws://{BROWSER_VNC_HOST}:{cdp_proxy_port}/")
                    ws_url = ws_url.replace("ws://127.0.0.1/", f"ws://{BROWSER_VNC_HOST}:{cdp_proxy_port}/")
                    logger.info(f"CDP WebSocket URL obtenida: {ws_url}")
                    return ws_url
        except Exception as e:
            logger.warning(f"No se pudo obtener CDP URL del navegador remoto: {e}")
        
        return None
    
    async def initialize(self) -> bool:
        """Inicializar Playwright - conectar al navegador remoto o crear uno local"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright no está instalado")
            return False
        
        async with self._lock:
            if self._browser:
                return True
            
            try:
                self._playwright = await async_playwright().start()
                
                # Intentar conectar al navegador remoto del browser-service
                cdp_url = await self._get_remote_cdp_url()
                if cdp_url:
                    try:
                        logger.info(f"Conectando al navegador remoto via CDP: {cdp_url}")
                        self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
                        self._is_remote = True
                        logger.info("✓ Conectado al navegador remoto - Las acciones serán visibles en VNC")
                        return True
                    except Exception as e:
                        logger.warning(f"No se pudo conectar al navegador remoto: {e}")
                
                # Fallback: iniciar navegador local headless
                logger.info("Iniciando navegador local headless como fallback...")
                self._browser = await self._playwright.chromium.launch(
                    headless=True,  # Siempre headless en fallback
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu'
                    ]
                )
                self._is_remote = False
                logger.info("Navegador Chromium local iniciado (headless)")
                return True
                
            except Exception as e:
                logger.error(f"Error iniciando Playwright: {e}")
                return False
    
    async def get_or_create_session(self, session_id: str = None) -> Optional[BrowserSession]:
        """Obtener o crear una sesión de navegador"""
        session_id = session_id or self._default_session_id
        
        if session_id in self._sessions and self._sessions[session_id].is_active:
            return self._sessions[session_id]
        
        # Asegurar que el navegador está inicializado
        if not self._browser:
            initialized = await self.initialize()
            if not initialized:
                return None
        
        try:
            # Para navegador remoto, usar el context y página existentes
            if self._is_remote:
                contexts = self._browser.contexts
                if contexts:
                    context = contexts[0]
                    pages = context.pages
                    if pages:
                        page = pages[0]
                    else:
                        page = await context.new_page()
                else:
                    # Si no hay contexts, crear uno nuevo (raro para remoto)
                    context = await self._browser.new_context()
                    page = await context.new_page()
            else:
                # Para navegador local, crear un nuevo context
                context = await self._browser.new_context(
                    viewport={'width': 1600, 'height': 900},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
            
            session = BrowserSession(
                id=session_id,
                browser=self._browser,
                context=context,
                page=page,
                is_active=True
            )
            self._sessions[session_id] = session
            
            logger.info(f"Sesión de navegador creada: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creando sesión: {e}")
            return None
    
    async def navigate(
        self,
        url: str,
        session_id: str = None,
        wait_until: str = "domcontentloaded"
    ) -> Dict[str, Any]:
        """Navegar a una URL"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No se pudo crear sesión de navegador"}
        
        try:
            response = await session.page.goto(url, wait_until=wait_until, timeout=30000)
            
            return {
                "success": True,
                "url": session.page.url,
                "title": await session.page.title(),
                "status": response.status if response else None
            }
        except Exception as e:
            logger.error(f"Error navegando a {url}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_content(
        self,
        session_id: str = None,
        selector: str = "body"
    ) -> Dict[str, Any]:
        """Obtener contenido de texto de la página"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesión activa"}
        
        try:
            # Obtener texto visible
            text = await session.page.inner_text(selector)
            
            # Obtener título
            title = await session.page.title()
            
            # Obtener URL actual
            url = session.page.url
            
            return {
                "success": True,
                "url": url,
                "title": title,
                "text": text[:10000],  # Limitar a 10k caracteres
                "truncated": len(text) > 10000
            }
        except Exception as e:
            logger.error(f"Error obteniendo contenido: {e}")
            return {"success": False, "error": str(e)}
    
    async def screenshot(
        self,
        session_id: str = None,
        full_page: bool = False
    ) -> Dict[str, Any]:
        """Tomar captura de pantalla"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesión activa"}
        
        try:
            screenshot_bytes = await session.page.screenshot(
                full_page=full_page,
                type="png"
            )
            
            # Convertir a base64
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            
            return {
                "success": True,
                "image": screenshot_b64,
                "mime_type": "image/png",
                "url": session.page.url
            }
        except Exception as e:
            logger.error(f"Error tomando screenshot: {e}")
            return {"success": False, "error": str(e)}
    
    async def click(
        self,
        selector: str,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Hacer clic en un elemento"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesión activa"}
        
        try:
            await session.page.click(selector, timeout=10000)
            await session.page.wait_for_load_state("domcontentloaded")
            
            return {
                "success": True,
                "clicked": selector,
                "url": session.page.url
            }
        except Exception as e:
            logger.error(f"Error haciendo clic en {selector}: {e}")
            return {"success": False, "error": str(e)}
    
    async def type_text(
        self,
        selector: str,
        text: str,
        session_id: str = None,
        press_enter: bool = False
    ) -> Dict[str, Any]:
        """Escribir texto en un campo"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesión activa"}
        
        try:
            await session.page.fill(selector, text, timeout=10000)
            
            if press_enter:
                await session.page.press(selector, "Enter")
                await session.page.wait_for_load_state("domcontentloaded")
            
            return {
                "success": True,
                "typed": text,
                "selector": selector,
                "url": session.page.url
            }
        except Exception as e:
            logger.error(f"Error escribiendo en {selector}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_elements(
        self,
        selector: str = "*",
        session_id: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Obtener elementos de la página"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesión activa"}
        
        try:
            # Obtener elementos interactivos
            elements = await session.page.query_selector_all(
                "a, button, input, textarea, select, [role='button'], [onclick]"
            )
            
            result = []
            for i, el in enumerate(elements[:limit]):
                try:
                    tag = await el.evaluate("el => el.tagName.toLowerCase()")
                    text = await el.inner_text() if tag not in ['input', 'textarea'] else ""
                    placeholder = await el.get_attribute("placeholder") or ""
                    href = await el.get_attribute("href") or ""
                    el_type = await el.get_attribute("type") or ""
                    name = await el.get_attribute("name") or ""
                    
                    result.append({
                        "index": i,
                        "tag": tag,
                        "text": text[:100].strip() if text else "",
                        "placeholder": placeholder,
                        "href": href[:200] if href else "",
                        "type": el_type,
                        "name": name
                    })
                except Exception:
                    continue
            
            return {
                "success": True,
                "elements": result,
                "total": len(elements),
                "url": session.page.url
            }
        except Exception as e:
            logger.error(f"Error obteniendo elementos: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_script(
        self,
        script: str,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Ejecutar JavaScript en la página"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesión activa"}
        
        try:
            result = await session.page.evaluate(script)
            
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Error ejecutando script: {e}")
            return {"success": False, "error": str(e)}
    
    async def close_session(self, session_id: str = None):
        """Cerrar una sesión de navegador"""
        session_id = session_id or self._default_session_id
        
        if session_id in self._sessions:
            session = self._sessions[session_id]
            try:
                if session.context:
                    await session.context.close()
                session.is_active = False
                del self._sessions[session_id]
                logger.info(f"Sesión cerrada: {session_id}")
            except Exception as e:
                logger.error(f"Error cerrando sesión {session_id}: {e}")
    
    async def shutdown(self):
        """Cerrar el servicio de navegador"""
        # Cerrar todas las sesiones
        for session_id in list(self._sessions.keys()):
            await self.close_session(session_id)
        
        # Cerrar el navegador
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        
        # Cerrar Playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        
        logger.info("Servicio de navegador cerrado")
    
    def get_tools_description(self) -> List[Dict[str, Any]]:
        """Obtener descripción de herramientas para el LLM"""
        return [
            {
                "name": "browser_navigate",
                "description": "Navegar a una URL en el navegador",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL a la que navegar"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "browser_get_content",
                "description": "Obtener el contenido de texto de la página actual",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "Selector CSS opcional", "default": "body"}
                    }
                }
            },
            {
                "name": "browser_screenshot",
                "description": "Tomar una captura de pantalla de la página",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "full_page": {"type": "boolean", "description": "Captura completa", "default": False}
                    }
                }
            },
            {
                "name": "browser_click",
                "description": "Hacer clic en un elemento de la página",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "Selector CSS del elemento"}
                    },
                    "required": ["selector"]
                }
            },
            {
                "name": "browser_type",
                "description": "Escribir texto en un campo de entrada",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "Selector CSS del campo"},
                        "text": {"type": "string", "description": "Texto a escribir"},
                        "press_enter": {"type": "boolean", "description": "Presionar Enter después", "default": False}
                    },
                    "required": ["selector", "text"]
                }
            },
            {
                "name": "browser_get_elements",
                "description": "Obtener lista de elementos interactivos de la página",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Máximo de elementos", "default": 50}
                    }
                }
            }
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del servicio de navegador"""
        # VNC está disponible si estamos conectados al navegador remoto
        vnc_available = self._is_remote and BROWSER_VNC_HOST is not None
        
        return {
            "initialized": self._browser is not None,
            "is_remote": self._is_remote,
            "headless": self._headless if not self._is_remote else False,
            "active_sessions": len([s for s in self._sessions.values() if s.is_active]),
            "vnc_available": vnc_available,
            "vnc_host": BROWSER_VNC_HOST if vnc_available else None
        }


# Instancia global del servicio
browser_service = BrowserService()
