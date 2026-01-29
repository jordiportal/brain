"""
Monitoring Middleware - Captura métricas de todas las requests HTTP
"""

import time
import asyncio
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware para capturar métricas de todas las requests HTTP.
    
    Captura:
    - Endpoint y método
    - Status code
    - Latencia
    - Tamaño de request/response
    - Errores
    """
    
    # Endpoints a excluir del tracking (health checks, etc.)
    EXCLUDED_PATHS = {
        "/health",
        "/health/ready",
        "/api/v1/monitoring/health",
        "/favicon.ico"
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Excluir ciertos paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Medir tiempo
        start_time = time.perf_counter()
        
        # Obtener tamaño de request
        request_size = 0
        if request.headers.get("content-length"):
            try:
                request_size = int(request.headers.get("content-length", 0))
            except ValueError:
                pass
        
        # Extraer user_id si está disponible (de headers o query params)
        user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id")
        
        # Ejecutar request
        error_message = None
        status_code = 500
        response_size = 0
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Intentar obtener tamaño de response
            if hasattr(response, "headers"):
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        response_size = int(content_length)
                    except ValueError:
                        pass
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Request error: {e}", path=request.url.path)
            raise
        
        finally:
            # Calcular latencia
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Guardar métrica (async, no bloquea la response)
            asyncio.create_task(
                self._save_metric(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    request_size=request_size,
                    response_size=response_size,
                    user_id=user_id,
                    error_message=error_message
                )
            )
        
        return response
    
    async def _save_metric(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
        request_size: int,
        response_size: int,
        user_id: str = None,
        error_message: str = None
    ) -> None:
        """Guardar métrica en la base de datos"""
        try:
            from ..monitoring import monitoring_service
            
            await monitoring_service.record_request(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                latency_ms=latency_ms,
                request_size=request_size,
                response_size=response_size,
                user_id=user_id,
                error_message=error_message
            )
            
        except Exception as e:
            # No fallar si hay error guardando métrica
            logger.warning(f"Error saving metric: {e}")
