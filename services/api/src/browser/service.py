"""
Browser Service - Servicio de navegaci?n web usando Playwright

Proporciona herramientas de navegaci?n web para los agentes.
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

# Configuraci?n
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
BROWSER_VNC_HOST = os.getenv("BROWSER_VNC_HOST", "browser")  # Host del servicio VNC
BROWSER_CDP_PORT = os.getenv("BROWSER_CDP_PORT", "9222")  # Puerto CDP del browser-service


@dataclass
class BrowserSession:
    """Sesi?n de navegador"""
    id: str
    browser: Optional[Any] = None
    context: Optional[Any] = None
    page: Optional[Any] = None
    is_active: bool = False


class BrowserService:
    """
    Servicio de navegaci?n web usando Playwright.
    
    Proporciona m?todos para:
    - Navegar a URLs
    - Hacer clic en elementos
    - Escribir texto
    - Tomar capturas de pantalla
    - Obtener contenido de la p?gina
    
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
    
    async def initialize(self, force: bool = False) -> bool:
        """Inicializar Playwright - conectar al navegador remoto o crear uno local"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright no est? instalado")
            return False
        
        async with self._lock:
            if self._browser and not force:
                # Verificar que la conexi?n sigue activa
                try:
                    if self._is_remote:
                        # Para remoto, verificar que hay contexts
                        _ = self._browser.contexts
                    return True
                except Exception:
                    logger.warning("Conexi?n al navegador perdida, reinicializando...")
                    self._browser = None
            
            try:
                self._playwright = await async_playwright().start()
                
                # Intentar conectar al navegador remoto del browser-service
                cdp_url = await self._get_remote_cdp_url()
                if cdp_url:
                    try:
                        logger.info(f"Conectando al navegador remoto via CDP: {cdp_url}")
                        self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
                        self._is_remote = True
                        logger.info("? Conectado al navegador remoto - Las acciones ser?n visibles en VNC")
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
    
    async def _reconnect(self) -> bool:
        """Reconectar al navegador si la conexi?n se perdi?"""
        logger.info("Intentando reconectar al navegador...")
        
        # Limpiar estado anterior
        self._browser = None
        self._sessions.clear()
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        
        # Reinicializar
        return await self.initialize()
    
    async def get_or_create_session(self, session_id: str = None) -> Optional[BrowserSession]:
        """Obtener o crear una sesi?n de navegador"""
        session_id = session_id or self._default_session_id
        
        if session_id in self._sessions and self._sessions[session_id].is_active:
            # Verificar que la p?gina sigue siendo v?lida
            try:
                session = self._sessions[session_id]
                if session.page:
                    # Intentar una operaci?n simple para verificar conexi?n
                    await session.page.evaluate("1")
                    return session
            except Exception:
                # La sesi?n no es v?lida, limpiarla
                logger.warning(f"Sesi?n {session_id} inv?lida, recreando...")
                del self._sessions[session_id]
        
        # Asegurar que el navegador est? inicializado
        if not self._browser:
            initialized = await self.initialize()
            if not initialized:
                return None
        
        try:
            # Para navegador remoto, usar el context y p?gina existentes
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
            
            logger.info(f"Sesi?n de navegador creada: {session_id}")
            return session
            
        except Exception as e:
            error_msg = str(e)
            # Si el error indica conexi?n perdida, intentar reconectar
            if "closed" in error_msg.lower() or "disconnected" in error_msg.lower():
                logger.warning("Conexi?n al navegador perdida, reconectando...")
                if await self._reconnect():
                    # Reintentar crear la sesi?n
                    return await self.get_or_create_session(session_id)
            
            logger.error(f"Error creando sesi?n: {e}")
            return None
    
    async def navigate(
        self,
        url: str,
        session_id: str = None,
        wait_until: str = "networkidle"
    ) -> Dict[str, Any]:
        """Navegar a una URL"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No se pudo crear sesión de navegador"}
        
        try:
            # Aumentar timeout y usar load para asegurar carga básica, luego networkidle
            response = await session.page.goto(url, wait_until="load", timeout=60000)
            
            try:
                await session.page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass
            
            # Esperar un momento extra para animaciones/popups
            await asyncio.sleep(2)
            
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
        """Obtener contenido de texto de la p?gina"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesi?n activa"}
        
        try:
            # Obtener texto visible
            text = await session.page.inner_text(selector)
            
            # Obtener t?tulo
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
            return {"success": False, "error": "No hay sesi?n activa"}
        
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
        """Hacer clic en un elemento (busca en página principal e iframes)"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesión activa"}
        
        try:
            # 0. Si el selector es texto puro (sin caracteres de selector CSS)
            if not any(c in selector for c in ['#', '.', '[', '=', '>', ':']):
                try:
                    locators = [
                        session.page.get_by_role("button", name=selector, exact=False),
                        session.page.get_by_text(selector, exact=False),
                        session.page.get_by_role("link", name=selector, exact=False)
                    ]
                    for loc in locators:
                        if await loc.count() > 0:
                            await loc.first.click(timeout=5000)
                            # Usar networkidle después de clics importantes (como aceptar cookies)
                            try:
                                await session.page.wait_for_load_state("networkidle", timeout=5000)
                            except:
                                await session.page.wait_for_load_state("domcontentloaded", timeout=2000)
                            return {
                                "success": True,
                                "clicked": f"element with text '{selector}'",
                                "url": session.page.url,
                                "frame": "main"
                            }
                except Exception:
                    pass

            # 1. Intentar en la página principal
            try:
                await session.page.click(selector, timeout=5000)
                try:
                    await session.page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    await session.page.wait_for_load_state("domcontentloaded", timeout=2000)
                return {
                    "success": True,
                    "clicked": selector,
                    "url": session.page.url,
                    "frame": "main"
                }
            except Exception:
                pass
            
            # 2. Intentar en iframes
            for frame in session.page.frames:
                if frame == session.page.main_frame:
                    continue
                try:
                    await frame.click(selector, timeout=3000)
                    await session.page.wait_for_load_state("domcontentloaded")
                    return {
                        "success": True,
                        "clicked": selector,
                        "url": session.page.url,
                        "frame": "iframe"
                    }
                except Exception:
                    continue
            
            # 3. Si no funcion?, intentar con locator m?s flexible
            try:
                # Intentar buscar por texto contenido
                if not selector.startswith(('.', '#', '[')) and ':' not in selector:
                    # Parece texto plano, buscar bot?n con ese texto
                    await session.page.get_by_role("button", name=selector).click(timeout=5000)
                    await session.page.wait_for_load_state("domcontentloaded")
                    return {
                        "success": True,
                        "clicked": f"button with text '{selector}'",
                        "url": session.page.url,
                        "frame": "main"
                    }
            except Exception:
                pass
            
            return {"success": False, "error": f"No se encontr? elemento: {selector}"}
            
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
            # 0. Si el selector parece una descripción de texto
            if not any(c in selector for c in ['#', '.', '[', '=', '>', ':']):
                try:
                    locators = [
                        session.page.get_by_placeholder(selector, exact=False),
                        session.page.get_by_role("textbox", name=selector, exact=False),
                        session.page.get_by_label(selector, exact=False)
                    ]
                    for loc in locators:
                        if await loc.count() > 0:
                            # Hacer clic antes de escribir para asegurar foco
                            await loc.first.click(timeout=3000)
                            await loc.first.fill(text, timeout=5000)
                            if press_enter:
                                await loc.first.press("Enter")
                                try:
                                    await session.page.wait_for_load_state("networkidle", timeout=5000)
                                except:
                                    await session.page.wait_for_load_state("domcontentloaded", timeout=2000)
                            return {
                                "success": True,
                                "typed": text,
                                "selector": f"element with text/label '{selector}'",
                                "url": session.page.url
                            }
                except Exception:
                    pass

            # 1. Intentar con selector estándar
            try:
                # Asegurar que el elemento esté visible
                await session.page.wait_for_selector(selector, state="visible", timeout=5000)
                # Hacer clic para asegurar foco y visibilidad (especialmente tras banners de cookies)
                await session.page.click(selector, timeout=3000)
                await session.page.fill(selector, text, timeout=5000)
                
                if press_enter:
                    await session.page.press(selector, "Enter")
                    try:
                        await session.page.wait_for_load_state("networkidle", timeout=5000)
                    except:
                        await session.page.wait_for_load_state("domcontentloaded", timeout=2000)
                
                return {
                    "success": True,
                    "typed": text,
                    "selector": selector,
                    "url": session.page.url
                }
            except Exception:
                # Fallback final: clic forzado y simulación de teclado
                try:
                    await session.page.click(selector, timeout=3000, force=True)
                    await session.page.keyboard.type(text)
                    if press_enter:
                        await session.page.keyboard.press("Enter")
                        try:
                            await session.page.wait_for_load_state("networkidle", timeout=5000)
                        except:
                            pass
                    return {
                        "success": True,
                        "typed": text,
                        "selector": f"{selector} (via forced click + keyboard)",
                        "url": session.page.url
                    }
                except Exception as inner_e:
                    return {"success": False, "error": f"Error tras múltiples intentos: {str(inner_e)}"}
        except Exception as e:
            logger.error(f"Error escribiendo en {selector}: {e}")
            return {"success": False, "error": str(e)}
    
    async def scroll(
        self,
        direction: str = "down",
        amount: int = 500,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Hacer scroll en la p?gina"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesi?n activa"}
        
        try:
            if direction == "down":
                await session.page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await session.page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "top":
                await session.page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                await session.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Esperar un momento para que se cargue contenido din?mico
            await asyncio.sleep(0.5)
            
            # Obtener posici?n actual
            scroll_pos = await session.page.evaluate("window.scrollY")
            scroll_height = await session.page.evaluate("document.body.scrollHeight")
            
            return {
                "success": True,
                "direction": direction,
                "amount": amount,
                "scroll_position": scroll_pos,
                "page_height": scroll_height,
                "url": session.page.url
            }
        except Exception as e:
            logger.error(f"Error haciendo scroll: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_elements(
        self,
        selector: str = "*",
        session_id: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Obtener elementos interactivos de la página, incluyendo iframes"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesión activa"}
        
        try:
            result = []
            # Selectores para elementos que suelen ser botones de cookies o importantes
            cookie_hints = "button:has-text('Aceptar'), button:has-text('Accept'), button:has-text('Agree'), button:has-text('Permitir'), button:has-text('Entendido'), button:has-text('OK'), button:has-text('Acepto'), button:has-text('I agree'), button:has-text('Consentir')"
            interactive_selector = f"a, button, input, textarea, select, [role='button'], [onclick], {cookie_hints}"
            
            # Asegurar que la página está cargada
            try:
                await session.page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            # Detectar si estamos en un diálogo de cookies de Google específicamente
            # para forzar su visibilidad o clic si es necesario
            is_google_cookies = "consent.google.com" in session.page.url
            
            # Selectores de cookies específicos para priorizar
            common_cookie_selectors = [
                "#L2AGLb", # Google "Aceptar todo"
                "button[aria-label*='Aceptar']",
                "button[aria-label*='Accept']",
                "#onetrust-accept-btn-handler", # OneTrust
                "#gdpr-banner-accept",
                "button[id*='accept']",
                "button[class*='accept']"
            ]
            
            # 1. Buscar en la página principal
            elements = await session.page.query_selector_all(interactive_selector)
            
            # Intentar añadir selectores específicos al inicio
            found_specials = []
            for sel in common_cookie_selectors:
                try:
                    el = await session.page.query_selector(sel)
                    if el:
                        found_specials.append(el)
                except:
                    continue
            
            # Combinar y evitar duplicados (manteniendo orden de prioridad)
            for el in reversed(found_specials):
                if el not in elements:
                    elements.insert(0, el)
            
            for i, el in enumerate(elements[:limit]):
                try:
                    # Omitir si no es visible
                    if not await el.is_visible():
                        continue
                        
                    tag = await el.evaluate("el => el.tagName.toLowerCase()")
                    text = await el.inner_text() if tag not in ['input', 'textarea'] else ""
                    placeholder = await el.get_attribute("placeholder") or ""
                    href = await el.get_attribute("href") or ""
                    el_type = await el.get_attribute("type") or ""
                    name = await el.get_attribute("name") or ""
                    el_id = await el.get_attribute("id") or ""
                    el_class = await el.get_attribute("class") or ""
                    aria_label = await el.get_attribute("aria-label") or ""
                    
                    # Limpiar texto de estilos/clases CSS incrustados
                    if text and text.startswith('.'):
                        text = ""
                    
                    result.append({
                        "index": len(result),
                        "tag": tag,
                        "text": text[:100].strip() if text else "",
                        "placeholder": placeholder,
                        "href": href[:200] if href else "",
                        "type": el_type,
                        "name": name,
                        "id": el_id,
                        "class": el_class[:100] if el_class else "",
                        "aria-label": aria_label,
                        "frame": "main"
                    })
                except Exception:
                    continue
            
            # 2. Buscar en iframes (importante para popups de cookies)
            try:
                frames = session.page.frames
                for frame in frames:
                    if frame == session.page.main_frame:
                        continue
                    try:
                        # Solo buscar en frames que parezcan cargados
                        frame_elements = await frame.query_selector_all(interactive_selector)
                        for el in frame_elements[:30]:
                            try:
                                if not await el.is_visible():
                                    continue
                                    
                                tag = await el.evaluate("el => el.tagName.toLowerCase()")
                                text = await el.inner_text() if tag not in ['input', 'textarea'] else ""
                                el_id = await el.get_attribute("id") or ""
                                el_class = await el.get_attribute("class") or ""
                                aria_label = await el.get_attribute("aria-label") or ""
                                
                                # A?adir si tiene texto, id, o es un input
                                if text.strip() or el_id or tag in ['input', 'textarea', 'button']:
                                    result.append({
                                        "index": len(result),
                                        "tag": tag,
                                        "text": text[:100].strip() if text else "",
                                        "placeholder": await el.get_attribute("placeholder") or "",
                                        "href": "",
                                        "type": await el.get_attribute("type") or "",
                                        "name": await el.get_attribute("name") or "",
                                        "id": el_id,
                                        "class": el_class[:100] if el_class else "",
                                        "aria-label": aria_label,
                                        "frame": "iframe"
                                    })
                            except Exception:
                                continue
                    except Exception:
                        continue
            except Exception:
                pass
            
            return {
                "success": True,
                "elements": result[:limit],
                "total": len(result),
                "url": session.page.url
            }
        except Exception as e:
            logger.error(f"Error obteniendo elementos: {e}")
            return {"success": False, "error": str(e)}
            
            # 2. Buscar en iframes (importante para popups de cookies)
            try:
                frames = session.page.frames
                for frame in frames:
                    if frame == session.page.main_frame:
                        continue
                    try:
                        # Scroll dentro del iframe para ver todos los elementos
                        try:
                            await frame.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await asyncio.sleep(0.2)
                            await frame.evaluate("window.scrollTo(0, 0)")
                        except Exception:
                            pass
                        
                        frame_elements = await frame.query_selector_all(interactive_selector)
                        for el in frame_elements[:30]:  # M?s elementos por iframe
                            try:
                                tag = await el.evaluate("el => el.tagName.toLowerCase()")
                                text = await el.inner_text() if tag not in ['input', 'textarea'] else ""
                                el_id = await el.get_attribute("id") or ""
                                el_class = await el.get_attribute("class") or ""
                                aria_label = await el.get_attribute("aria-label") or ""
                                
                                # A?adir si tiene texto, id, o es un input
                                if text.strip() or el_id or tag in ['input', 'textarea', 'button']:
                                    result.append({
                                        "index": len(result),
                                        "tag": tag,
                                        "text": text[:100].strip() if text else "",
                                        "placeholder": await el.get_attribute("placeholder") or "",
                                        "href": "",
                                        "type": await el.get_attribute("type") or "",
                                        "name": await el.get_attribute("name") or "",
                                        "id": el_id,
                                        "class": el_class[:100] if el_class else "",
                                        "aria-label": aria_label,
                                        "frame": "iframe"
                                    })
                            except Exception:
                                continue
                    except Exception:
                        continue
            except Exception:
                pass
            
            return {
                "success": True,
                "elements": result[:limit],
                "total": len(result),
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
        """Ejecutar JavaScript en la p?gina"""
        session = await self.get_or_create_session(session_id)
        if not session or not session.page:
            return {"success": False, "error": "No hay sesi?n activa"}
        
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
        """Cerrar una sesi?n de navegador"""
        session_id = session_id or self._default_session_id
        
        if session_id in self._sessions:
            session = self._sessions[session_id]
            try:
                if session.context:
                    await session.context.close()
                session.is_active = False
                del self._sessions[session_id]
                logger.info(f"Sesi?n cerrada: {session_id}")
            except Exception as e:
                logger.error(f"Error cerrando sesi?n {session_id}: {e}")
    
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
        """Obtener descripci?n de herramientas para el LLM"""
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
                "description": "Obtener el contenido de texto de la p?gina actual",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "Selector CSS opcional", "default": "body"}
                    }
                }
            },
            {
                "name": "browser_screenshot",
                "description": "Tomar una captura de pantalla de la p?gina",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "full_page": {"type": "boolean", "description": "Captura completa", "default": False}
                    }
                }
            },
            {
                "name": "browser_click",
                "description": "Hacer clic en un elemento de la p?gina",
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
                        "press_enter": {"type": "boolean", "description": "Presionar Enter despu?s", "default": False}
                    },
                    "required": ["selector", "text"]
                }
            },
            {
                "name": "browser_get_elements",
                "description": "Obtener lista de elementos interactivos de la p?gina",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "M?ximo de elementos", "default": 50}
                    }
                }
            },
            {
                "name": "browser_scroll",
                "description": "Hacer scroll en la p?gina para ver m?s contenido",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "description": "Direcci?n: down, up, top, bottom", "default": "down"},
                        "amount": {"type": "integer", "description": "P?xeles a desplazar (para down/up)", "default": 500}
                    }
                }
            }
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del servicio de navegador"""
        # VNC est? disponible si estamos conectados al navegador remoto
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
