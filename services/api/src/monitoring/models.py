"""
Monitoring Models - Pydantic models for monitoring data
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ApiMetric(BaseModel):
    """Métrica de una request API"""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    user_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ExecutionTrace(BaseModel):
    """Traza de ejecución de una chain/tool/LLM"""
    id: Optional[int] = None
    execution_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    chain_id: Optional[str] = None
    event_type: str  # 'chain_start', 'tool_call', 'llm_call', 'chain_end'
    node_id: Optional[str] = None
    duration_ms: Optional[float] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MonitoringAlert(BaseModel):
    """Alerta de monitorización"""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    alert_type: str  # 'error_rate', 'latency', 'token_limit', 'cost'
    severity: str  # 'info', 'warning', 'critical'
    message: str
    metadata: Optional[Dict[str, Any]] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class MetricsAggregation(BaseModel):
    """Métricas agregadas por período"""
    period: str  # 'hour', 'day', 'week'
    start_time: datetime
    end_time: datetime
    request_count: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_count: int = 0
    error_rate: float = 0.0
    success_count: int = 0
    endpoints: Dict[str, int] = Field(default_factory=dict)


class ChainStats(BaseModel):
    """Estadísticas de ejecución de chains"""
    chain_id: str
    execution_count: int = 0
    avg_duration_ms: float = 0.0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost_usd: float = 0.0
    error_count: int = 0
    success_rate: float = 0.0


class UserActivityStats(BaseModel):
    """Estadísticas de actividad por usuario"""
    active_users_today: int = 0
    active_users_7d: int = 0
    active_users_30d: int = 0
    total_registered_users: int = 0
    top_users: List[Dict[str, Any]] = Field(default_factory=list)
    hourly_active_users: List[Dict[str, Any]] = Field(default_factory=list)


class DashboardStats(BaseModel):
    """Estadísticas para el dashboard"""
    # Métricas en tiempo real
    requests_per_minute: float = 0.0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    active_executions: int = 0
    
    # Totales del período
    total_requests: int = 0
    total_errors: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    
    # Tendencias (últimas 24h)
    hourly_requests: List[Dict[str, Any]] = Field(default_factory=list)
    hourly_latency: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Top endpoints
    top_endpoints: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Chains stats
    chain_stats: List[ChainStats] = Field(default_factory=list)
    
    # Alertas activas
    active_alerts: int = 0
    critical_alerts: int = 0


# Request/Response models for API

class MetricsQueryParams(BaseModel):
    """Parámetros de consulta para métricas"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    endpoint: Optional[str] = None
    min_latency_ms: Optional[float] = None
    status_code: Optional[int] = None
    limit: int = 100
    offset: int = 0


class TracesQueryParams(BaseModel):
    """Parámetros de consulta para trazas"""
    execution_id: Optional[str] = None
    chain_id: Optional[str] = None
    event_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success: Optional[bool] = None
    limit: int = 100
    offset: int = 0


class AlertsQueryParams(BaseModel):
    """Parámetros de consulta para alertas"""
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    acknowledged: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


class AcknowledgeAlertRequest(BaseModel):
    """Request para marcar alerta como vista"""
    acknowledged_by: str
