"""
Monitoring Service - Core monitoring logic
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import structlog

from .repository import MonitoringRepository
from .models import (
    ApiMetric,
    ExecutionTrace,
    MonitoringAlert,
    DashboardStats,
    ChainStats
)

logger = structlog.get_logger()


# ============================================
# Alert Rules Configuration
# ============================================

ALERT_RULES = {
    "error_rate": {
        "threshold": 0.05,  # 5% error rate
        "window_minutes": 5,
        "severity": "critical",
        "message": "Error rate exceeded {value:.1%} (threshold: {threshold:.1%})"
    },
    "latency_p95": {
        "threshold_ms": 5000,  # 5 seconds
        "window_minutes": 5,
        "severity": "warning",
        "message": "P95 latency exceeded {value:.0f}ms (threshold: {threshold:.0f}ms)"
    },
    "daily_cost": {
        "threshold_usd": 10.0,
        "severity": "warning",
        "message": "Daily LLM cost exceeded ${value:.2f} (threshold: ${threshold:.2f})"
    }
}


class MonitoringService:
    """
    Servicio principal de monitorización.
    
    Responsabilidades:
    - Guardar métricas y trazas
    - Evaluar reglas de alertas
    - Proporcionar datos para dashboard
    """
    
    def __init__(self):
        self._initialized = False
        self._last_alert_check: Dict[str, datetime] = {}
    
    # ============================================
    # API Metrics
    # ============================================
    
    async def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        user_id: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registrar una métrica de request"""
        metric = ApiMetric(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            request_size=request_size,
            response_size=response_size,
            user_id=user_id,
            error_message=error_message,
            metadata=metadata
        )
        
        await MonitoringRepository.save_metric(metric)
        
        # Verificar alertas si hay error
        if status_code >= 500:
            asyncio.create_task(self._check_error_rate_alert())
    
    async def get_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApiMetric]:
        """Obtener métricas con filtros"""
        return await MonitoringRepository.get_metrics(
            start_time=start_time,
            end_time=end_time,
            endpoint=endpoint,
            status_code=status_code,
            limit=limit,
            offset=offset
        )
    
    # ============================================
    # Execution Traces
    # ============================================
    
    async def trace_start(
        self,
        execution_id: str,
        chain_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registrar inicio de ejecución"""
        trace = ExecutionTrace(
            execution_id=execution_id,
            chain_id=chain_id,
            event_type="chain_start",
            metadata=metadata
        )
        await MonitoringRepository.save_trace(trace)
    
    async def trace_tool(
        self,
        execution_id: str,
        chain_id: str,
        tool_name: str,
        duration_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registrar llamada a tool"""
        trace = ExecutionTrace(
            execution_id=execution_id,
            chain_id=chain_id,
            event_type="tool_call",
            node_id=tool_name,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        await MonitoringRepository.save_trace(trace)
    
    async def trace_llm(
        self,
        execution_id: str,
        chain_id: str,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
        duration_ms: float,
        cost_usd: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registrar llamada a LLM"""
        # Calcular coste si no se proporciona
        if cost_usd is None:
            cost_usd = self._estimate_cost(provider, model, tokens_input, tokens_output)
        
        trace = ExecutionTrace(
            execution_id=execution_id,
            chain_id=chain_id,
            event_type="llm_call",
            provider=provider,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        await MonitoringRepository.save_trace(trace)
        
        # Verificar coste diario
        asyncio.create_task(self._check_daily_cost_alert())
    
    async def trace_end(
        self,
        execution_id: str,
        chain_id: str,
        duration_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registrar fin de ejecución"""
        trace = ExecutionTrace(
            execution_id=execution_id,
            chain_id=chain_id,
            event_type="chain_end",
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        await MonitoringRepository.save_trace(trace)
    
    async def get_execution_trace(self, execution_id: str) -> List[ExecutionTrace]:
        """Obtener traza completa de una ejecución"""
        return await MonitoringRepository.get_execution_trace(execution_id)
    
    async def get_traces(
        self,
        execution_id: Optional[str] = None,
        chain_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ExecutionTrace]:
        """Obtener trazas con filtros"""
        return await MonitoringRepository.get_traces(
            execution_id=execution_id,
            chain_id=chain_id,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
    
    # ============================================
    # Alerts
    # ============================================
    
    async def get_alerts(
        self,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MonitoringAlert]:
        """Obtener alertas"""
        return await MonitoringRepository.get_alerts(
            alert_type=alert_type,
            severity=severity,
            acknowledged=acknowledged,
            limit=limit,
            offset=offset
        )
    
    async def acknowledge_alert(self, alert_id: int, acknowledged_by: str) -> bool:
        """Marcar alerta como reconocida"""
        return await MonitoringRepository.acknowledge_alert(alert_id, acknowledged_by)
    
    async def create_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Crear una alerta manualmente"""
        alert = MonitoringAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            metadata=metadata
        )
        return await MonitoringRepository.save_alert(alert)
    
    # ============================================
    # Dashboard
    # ============================================
    
    async def get_dashboard_stats(self) -> DashboardStats:
        """Obtener estadísticas para el dashboard"""
        
        # Stats en tiempo real
        realtime = await MonitoringRepository.get_realtime_stats()
        
        # Alertas activas
        alerts_count = await MonitoringRepository.get_active_alerts_count()
        
        # Top endpoints
        top_endpoints = await MonitoringRepository.get_top_endpoints(10)
        
        # Datos por hora (últimas 24h)
        hourly_data = await MonitoringRepository.get_hourly_data(24)
        
        # Stats de chains (últimos 7 días)
        chain_stats = await MonitoringRepository.get_chain_stats()
        
        # Totales del día
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_metrics = await MonitoringRepository.get_metrics_aggregation(
            start_time=today_start,
            end_time=datetime.utcnow(),
            group_by='day'
        )
        
        total_requests = 0
        total_errors = 0
        if today_metrics:
            total_requests = today_metrics[0].request_count
            total_errors = today_metrics[0].error_count
        
        # Tokens y coste del día
        total_tokens = 0
        total_cost = 0.0
        for stat in chain_stats:
            total_tokens += stat.total_tokens_input + stat.total_tokens_output
            total_cost += stat.total_cost_usd
        
        return DashboardStats(
            requests_per_minute=realtime['requests_per_minute'],
            avg_latency_ms=realtime['avg_latency_ms'],
            error_rate=realtime['error_rate'],
            active_executions=0,  # TODO: Implementar tracking de ejecuciones activas
            total_requests=total_requests,
            total_errors=total_errors,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            hourly_requests=[
                {"hour": h['hour'], "count": h['request_count']}
                for h in hourly_data
            ],
            hourly_latency=[
                {"hour": h['hour'], "latency": h['avg_latency_ms']}
                for h in hourly_data
            ],
            top_endpoints=top_endpoints,
            chain_stats=chain_stats,
            active_alerts=alerts_count['total'],
            critical_alerts=alerts_count['critical']
        )
    
    # ============================================
    # Alert Evaluation
    # ============================================
    
    async def _check_error_rate_alert(self) -> None:
        """Verificar alerta de error rate"""
        rule = ALERT_RULES["error_rate"]
        
        # Evitar spam de alertas
        last_check = self._last_alert_check.get("error_rate")
        if last_check and datetime.utcnow() - last_check < timedelta(minutes=1):
            return
        
        self._last_alert_check["error_rate"] = datetime.utcnow()
        
        # Calcular error rate
        window_start = datetime.utcnow() - timedelta(minutes=rule["window_minutes"])
        metrics = await MonitoringRepository.get_metrics(start_time=window_start)
        
        if len(metrics) < 10:  # Mínimo de requests para calcular
            return
        
        error_count = sum(1 for m in metrics if m.status_code >= 500)
        error_rate = error_count / len(metrics)
        
        if error_rate > rule["threshold"]:
            message = rule["message"].format(
                value=error_rate,
                threshold=rule["threshold"]
            )
            await self.create_alert(
                alert_type="error_rate",
                severity=rule["severity"],
                message=message,
                metadata={
                    "error_rate": error_rate,
                    "error_count": error_count,
                    "total_requests": len(metrics),
                    "window_minutes": rule["window_minutes"]
                }
            )
            logger.warning(f"Alert created: {message}")
    
    async def _check_daily_cost_alert(self) -> None:
        """Verificar alerta de coste diario"""
        rule = ALERT_RULES["daily_cost"]
        
        # Evitar spam de alertas
        last_check = self._last_alert_check.get("daily_cost")
        if last_check and datetime.utcnow() - last_check < timedelta(minutes=10):
            return
        
        self._last_alert_check["daily_cost"] = datetime.utcnow()
        
        # Calcular coste del día
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        chain_stats = await MonitoringRepository.get_chain_stats(
            start_time=today_start,
            end_time=datetime.utcnow()
        )
        
        total_cost = sum(stat.total_cost_usd for stat in chain_stats)
        
        if total_cost > rule["threshold_usd"]:
            message = rule["message"].format(
                value=total_cost,
                threshold=rule["threshold_usd"]
            )
            await self.create_alert(
                alert_type="daily_cost",
                severity=rule["severity"],
                message=message,
                metadata={
                    "total_cost_usd": total_cost,
                    "threshold_usd": rule["threshold_usd"]
                }
            )
            logger.warning(f"Alert created: {message}")
    
    # ============================================
    # Cost Estimation
    # ============================================
    
    def _estimate_cost(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int
    ) -> float:
        """Estimar coste de una llamada LLM"""
        
        # Precios aproximados por 1M tokens (actualizar según necesidad)
        PRICING = {
            "openai": {
                "gpt-4": {"input": 30.0, "output": 60.0},
                "gpt-4-turbo": {"input": 10.0, "output": 30.0},
                "gpt-4o": {"input": 5.0, "output": 15.0},
                "gpt-4o-mini": {"input": 0.15, "output": 0.60},
                "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
            },
            "anthropic": {
                "claude-3-opus": {"input": 15.0, "output": 75.0},
                "claude-3-sonnet": {"input": 3.0, "output": 15.0},
                "claude-3-haiku": {"input": 0.25, "output": 1.25},
            },
            "google": {
                "gemini-pro": {"input": 0.5, "output": 1.5},
                "gemini-1.5-pro": {"input": 3.5, "output": 10.5},
            }
        }
        
        # Ollama y otros locales son gratis
        if provider in ["ollama", "local"]:
            return 0.0
        
        # Buscar precio
        provider_prices = PRICING.get(provider, {})
        
        # Buscar modelo exacto o parcial
        model_price = None
        for model_key, price in provider_prices.items():
            if model_key in model.lower():
                model_price = price
                break
        
        if not model_price:
            # Precio por defecto si no se encuentra
            return 0.0
        
        # Calcular coste
        input_cost = (tokens_input / 1_000_000) * model_price["input"]
        output_cost = (tokens_output / 1_000_000) * model_price["output"]
        
        return input_cost + output_cost


# Instancia global del servicio
monitoring_service = MonitoringService()
