"""
Monitoring Router - API endpoints for monitoring
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .service import monitoring_service
from .models import (
    ApiMetric,
    ExecutionTrace,
    MonitoringAlert,
    DashboardStats,
    AcknowledgeAlertRequest
)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


# ============================================
# Response Models
# ============================================

class MetricsResponse(BaseModel):
    metrics: List[ApiMetric]
    total: int


class TracesResponse(BaseModel):
    traces: List[ExecutionTrace]
    total: int


class AlertsResponse(BaseModel):
    alerts: List[MonitoringAlert]
    total: int


class ExecutionDetailResponse(BaseModel):
    execution_id: str
    traces: List[ExecutionTrace]
    summary: dict


# ============================================
# Dashboard
# ============================================

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard():
    """
    Obtener estadísticas del dashboard.
    
    Incluye:
    - Métricas en tiempo real (requests/min, latencia, error rate)
    - Totales del día
    - Datos por hora (últimas 24h)
    - Top endpoints
    - Estadísticas de chains
    - Alertas activas
    """
    return await monitoring_service.get_dashboard_stats()


# ============================================
# Metrics
# ============================================

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    start_time: Optional[datetime] = Query(None, description="Inicio del período"),
    end_time: Optional[datetime] = Query(None, description="Fin del período"),
    endpoint: Optional[str] = Query(None, description="Filtrar por endpoint"),
    status_code: Optional[int] = Query(None, description="Filtrar por status code"),
    limit: int = Query(100, le=1000, description="Límite de resultados"),
    offset: int = Query(0, description="Offset para paginación")
):
    """
    Obtener métricas de API con filtros.
    """
    # Defaults
    if not start_time:
        start_time = datetime.utcnow() - timedelta(hours=24)
    if not end_time:
        end_time = datetime.utcnow()
    
    metrics = await monitoring_service.get_metrics(
        start_time=start_time,
        end_time=end_time,
        endpoint=endpoint,
        status_code=status_code,
        limit=limit,
        offset=offset
    )
    
    return MetricsResponse(metrics=metrics, total=len(metrics))


@router.get("/metrics/aggregated")
async def get_metrics_aggregated(
    period: str = Query("hour", description="Período de agregación: hour, day"),
    hours: int = Query(24, le=168, description="Horas hacia atrás")
):
    """
    Obtener métricas agregadas por período.
    """
    from .repository import MonitoringRepository
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    end_time = datetime.utcnow()
    
    aggregations = await MonitoringRepository.get_metrics_aggregation(
        start_time=start_time,
        end_time=end_time,
        group_by=period
    )
    
    return {
        "period": period,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "data": [a.model_dump() for a in aggregations]
    }


# ============================================
# Traces
# ============================================

@router.get("/traces", response_model=TracesResponse)
async def get_traces(
    execution_id: Optional[str] = Query(None, description="Filtrar por execution_id"),
    chain_id: Optional[str] = Query(None, description="Filtrar por chain_id"),
    event_type: Optional[str] = Query(None, description="Filtrar por tipo: chain_start, tool_call, llm_call, chain_end"),
    start_time: Optional[datetime] = Query(None, description="Inicio del período"),
    end_time: Optional[datetime] = Query(None, description="Fin del período"),
    limit: int = Query(100, le=1000, description="Límite de resultados"),
    offset: int = Query(0, description="Offset para paginación")
):
    """
    Obtener trazas de ejecución con filtros.
    """
    # Defaults
    if not start_time:
        start_time = datetime.utcnow() - timedelta(hours=24)
    if not end_time:
        end_time = datetime.utcnow()
    
    traces = await monitoring_service.get_traces(
        execution_id=execution_id,
        chain_id=chain_id,
        event_type=event_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )
    
    return TracesResponse(traces=traces, total=len(traces))


@router.get("/traces/{execution_id}", response_model=ExecutionDetailResponse)
async def get_execution_detail(execution_id: str):
    """
    Obtener traza completa de una ejecución específica.
    """
    traces = await monitoring_service.get_execution_trace(execution_id)
    
    if not traces:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    
    # Calcular resumen
    chain_start = next((t for t in traces if t.event_type == "chain_start"), None)
    chain_end = next((t for t in traces if t.event_type == "chain_end"), None)
    llm_calls = [t for t in traces if t.event_type == "llm_call"]
    tool_calls = [t for t in traces if t.event_type == "tool_call"]
    
    summary = {
        "chain_id": chain_start.chain_id if chain_start else None,
        "start_time": chain_start.timestamp.isoformat() if chain_start else None,
        "end_time": chain_end.timestamp.isoformat() if chain_end else None,
        "duration_ms": chain_end.duration_ms if chain_end else None,
        "success": chain_end.success if chain_end else None,
        "llm_calls_count": len(llm_calls),
        "tool_calls_count": len(tool_calls),
        "total_tokens_input": sum(t.tokens_input or 0 for t in llm_calls),
        "total_tokens_output": sum(t.tokens_output or 0 for t in llm_calls),
        "total_cost_usd": sum(t.cost_usd or 0 for t in llm_calls),
        "tools_used": list(set(t.node_id for t in tool_calls if t.node_id))
    }
    
    return ExecutionDetailResponse(
        execution_id=execution_id,
        traces=traces,
        summary=summary
    )


@router.get("/traces/recent/executions")
async def get_recent_executions(
    limit: int = Query(20, le=100, description="Número de ejecuciones")
):
    """
    Obtener lista de ejecuciones recientes con resumen.
    """
    from .repository import MonitoringRepository
    
    # Obtener chain_end events para tener ejecuciones completas
    traces = await MonitoringRepository.get_traces(
        event_type="chain_end",
        limit=limit
    )
    
    executions = []
    for trace in traces:
        executions.append({
            "execution_id": trace.execution_id,
            "chain_id": trace.chain_id,
            "timestamp": trace.timestamp.isoformat(),
            "duration_ms": trace.duration_ms,
            "success": trace.success,
            "error_message": trace.error_message
        })
    
    return {"executions": executions, "total": len(executions)}


# ============================================
# Chain Stats
# ============================================

@router.get("/chains/stats")
async def get_chain_stats(
    days: int = Query(7, le=30, description="Días hacia atrás")
):
    """
    Obtener estadísticas por chain.
    """
    from .repository import MonitoringRepository
    
    start_time = datetime.utcnow() - timedelta(days=days)
    stats = await MonitoringRepository.get_chain_stats(
        start_time=start_time,
        end_time=datetime.utcnow()
    )
    
    return {
        "period_days": days,
        "chains": [s.model_dump() for s in stats]
    }


# ============================================
# Alerts
# ============================================

@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    alert_type: Optional[str] = Query(None, description="Tipo de alerta"),
    severity: Optional[str] = Query(None, description="Severidad: info, warning, critical"),
    acknowledged: Optional[bool] = Query(None, description="Filtrar por estado"),
    limit: int = Query(50, le=200, description="Límite de resultados"),
    offset: int = Query(0, description="Offset para paginación")
):
    """
    Obtener alertas con filtros.
    """
    alerts = await monitoring_service.get_alerts(
        alert_type=alert_type,
        severity=severity,
        acknowledged=acknowledged,
        limit=limit,
        offset=offset
    )
    
    return AlertsResponse(alerts=alerts, total=len(alerts))


@router.get("/alerts/active")
async def get_active_alerts():
    """
    Obtener resumen de alertas activas.
    """
    from .repository import MonitoringRepository
    
    counts = await MonitoringRepository.get_active_alerts_count()
    alerts = await monitoring_service.get_alerts(acknowledged=False, limit=10)
    
    return {
        "counts": counts,
        "recent": [a.model_dump() for a in alerts]
    }


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    request: AcknowledgeAlertRequest
):
    """
    Marcar una alerta como reconocida.
    """
    success = await monitoring_service.acknowledge_alert(
        alert_id=alert_id,
        acknowledged_by=request.acknowledged_by
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    
    return {"status": "ok", "alert_id": alert_id, "acknowledged": True}


# ============================================
# Health & Status
# ============================================

@router.get("/health")
async def monitoring_health():
    """
    Estado del sistema de monitorización.
    """
    from .repository import MonitoringRepository
    
    try:
        # Verificar que podemos leer de las tablas
        await MonitoringRepository.get_realtime_stats()
        
        return {
            "status": "healthy",
            "message": "Monitoring system operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": str(e)
        }
