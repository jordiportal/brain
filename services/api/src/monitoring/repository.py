"""
Monitoring Repository - Database access for monitoring tables
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import structlog

from ..db.connection import get_db
from .models import (
    ApiMetric,
    ExecutionTrace,
    MonitoringAlert,
    MetricsAggregation,
    ChainStats
)

logger = structlog.get_logger()


class MonitoringRepository:
    """Repository para acceso a tablas de monitorización"""
    
    # ============================================
    # API Metrics
    # ============================================
    
    @staticmethod
    async def save_metric(metric: ApiMetric) -> int:
        """Guardar una métrica de API"""
        db = get_db()
        
        query = """
            INSERT INTO api_metrics 
            (timestamp, endpoint, method, status_code, latency_ms, 
             request_size, response_size, user_id, error_message, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
            RETURNING id
        """
        
        try:
            result = await db.fetch_one(
                query,
                metric.timestamp,
                metric.endpoint,
                metric.method,
                metric.status_code,
                metric.latency_ms,
                metric.request_size,
                metric.response_size,
                metric.user_id,
                metric.error_message,
                json.dumps(metric.metadata) if metric.metadata else None
            )
            return result['id'] if result else 0
        except Exception as e:
            logger.error(f"Error saving metric: {e}")
            return 0
    
    @staticmethod
    async def get_metrics(
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApiMetric]:
        """Obtener métricas con filtros"""
        db = get_db()
        
        conditions = ["1=1"]
        params = []
        param_idx = 1
        
        if start_time:
            conditions.append(f"timestamp >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"timestamp <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        if endpoint:
            conditions.append(f"endpoint = ${param_idx}")
            params.append(endpoint)
            param_idx += 1
        
        if status_code:
            conditions.append(f"status_code = ${param_idx}")
            params.append(status_code)
            param_idx += 1
        
        query = f"""
            SELECT * FROM api_metrics
            WHERE {' AND '.join(conditions)}
            ORDER BY timestamp DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])
        
        rows = await db.fetch_all(query, *params)
        return [MonitoringRepository._row_to_metric(row) for row in rows]
    
    @staticmethod
    async def get_metrics_aggregation(
        start_time: datetime,
        end_time: datetime,
        group_by: str = 'hour'
    ) -> List[MetricsAggregation]:
        """Obtener métricas agregadas por período"""
        db = get_db()
        
        query = f"""
            SELECT 
                date_trunc($1, timestamp) as period_start,
                COUNT(*) as request_count,
                AVG(latency_ms) as avg_latency_ms,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
                COUNT(*) FILTER (WHERE status_code >= 500) as error_count,
                COUNT(*) FILTER (WHERE status_code >= 200 AND status_code < 300) as success_count
            FROM api_metrics
            WHERE timestamp >= $2 AND timestamp <= $3
            GROUP BY date_trunc($1, timestamp)
            ORDER BY period_start DESC
        """
        
        rows = await db.fetch_all(query, group_by, start_time, end_time)
        
        aggregations = []
        for row in rows:
            request_count = row['request_count'] or 0
            error_count = row['error_count'] or 0
            
            aggregations.append(MetricsAggregation(
                period=group_by,
                start_time=row['period_start'],
                end_time=row['period_start'] + timedelta(hours=1 if group_by == 'hour' else 24),
                request_count=request_count,
                avg_latency_ms=row['avg_latency_ms'] or 0.0,
                p95_latency_ms=row['p95_latency_ms'] or 0.0,
                error_count=error_count,
                error_rate=error_count / request_count if request_count > 0 else 0.0,
                success_count=row['success_count'] or 0
            ))
        
        return aggregations
    
    # ============================================
    # Execution Traces
    # ============================================
    
    @staticmethod
    async def save_trace(trace: ExecutionTrace) -> int:
        """Guardar una traza de ejecución"""
        db = get_db()
        
        query = """
            INSERT INTO execution_traces 
            (execution_id, timestamp, chain_id, event_type, node_id,
             duration_ms, tokens_input, tokens_output, cost_usd,
             provider, model, success, error_message, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14::jsonb)
            RETURNING id
        """
        
        try:
            result = await db.fetch_one(
                query,
                trace.execution_id,
                trace.timestamp,
                trace.chain_id,
                trace.event_type,
                trace.node_id,
                trace.duration_ms,
                trace.tokens_input,
                trace.tokens_output,
                trace.cost_usd,
                trace.provider,
                trace.model,
                trace.success,
                trace.error_message,
                json.dumps(trace.metadata) if trace.metadata else None
            )
            return result['id'] if result else 0
        except Exception as e:
            logger.error(f"Error saving trace: {e}")
            return 0
    
    @staticmethod
    async def get_traces(
        execution_id: Optional[str] = None,
        chain_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ExecutionTrace]:
        """Obtener trazas con filtros"""
        db = get_db()
        
        conditions = ["1=1"]
        params = []
        param_idx = 1
        
        if execution_id:
            conditions.append(f"execution_id = ${param_idx}")
            params.append(execution_id)
            param_idx += 1
        
        if chain_id:
            conditions.append(f"chain_id = ${param_idx}")
            params.append(chain_id)
            param_idx += 1
        
        if event_type:
            conditions.append(f"event_type = ${param_idx}")
            params.append(event_type)
            param_idx += 1
        
        if start_time:
            conditions.append(f"timestamp >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"timestamp <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        query = f"""
            SELECT * FROM execution_traces
            WHERE {' AND '.join(conditions)}
            ORDER BY timestamp DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])
        
        rows = await db.fetch_all(query, *params)
        return [MonitoringRepository._row_to_trace(row) for row in rows]
    
    @staticmethod
    async def get_execution_trace(execution_id: str) -> List[ExecutionTrace]:
        """Obtener traza completa de una ejecución"""
        db = get_db()
        
        query = """
            SELECT * FROM execution_traces
            WHERE execution_id = $1
            ORDER BY timestamp ASC
        """
        
        rows = await db.fetch_all(query, execution_id)
        return [MonitoringRepository._row_to_trace(row) for row in rows]
    
    @staticmethod
    async def get_chain_stats(
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ChainStats]:
        """Obtener estadísticas por chain"""
        db = get_db()
        
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        if not end_time:
            end_time = datetime.utcnow()
        
        query = """
            SELECT 
                chain_id,
                COUNT(DISTINCT execution_id) as execution_count,
                AVG(duration_ms) FILTER (WHERE event_type = 'chain_end') as avg_duration_ms,
                SUM(tokens_input) as total_tokens_input,
                SUM(tokens_output) as total_tokens_output,
                SUM(cost_usd) as total_cost_usd,
                COUNT(*) FILTER (WHERE success = false AND event_type = 'chain_end') as error_count
            FROM execution_traces
            WHERE timestamp >= $1 AND timestamp <= $2 AND chain_id IS NOT NULL
            GROUP BY chain_id
            ORDER BY execution_count DESC
        """
        
        rows = await db.fetch_all(query, start_time, end_time)
        
        stats = []
        for row in rows:
            exec_count = row['execution_count'] or 0
            error_count = row['error_count'] or 0
            
            stats.append(ChainStats(
                chain_id=row['chain_id'],
                execution_count=exec_count,
                avg_duration_ms=row['avg_duration_ms'] or 0.0,
                total_tokens_input=row['total_tokens_input'] or 0,
                total_tokens_output=row['total_tokens_output'] or 0,
                total_cost_usd=row['total_cost_usd'] or 0.0,
                error_count=error_count,
                success_rate=(exec_count - error_count) / exec_count if exec_count > 0 else 0.0
            ))
        
        return stats
    
    # ============================================
    # Alerts
    # ============================================
    
    @staticmethod
    async def save_alert(alert: MonitoringAlert) -> int:
        """Guardar una alerta"""
        db = get_db()
        
        query = """
            INSERT INTO monitoring_alerts 
            (timestamp, alert_type, severity, message, metadata, acknowledged)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            RETURNING id
        """
        
        try:
            result = await db.fetch_one(
                query,
                alert.timestamp,
                alert.alert_type,
                alert.severity,
                alert.message,
                json.dumps(alert.metadata) if alert.metadata else None,
                alert.acknowledged
            )
            return result['id'] if result else 0
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
            return 0
    
    @staticmethod
    async def get_alerts(
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MonitoringAlert]:
        """Obtener alertas con filtros"""
        db = get_db()
        
        conditions = ["1=1"]
        params = []
        param_idx = 1
        
        if alert_type:
            conditions.append(f"alert_type = ${param_idx}")
            params.append(alert_type)
            param_idx += 1
        
        if severity:
            conditions.append(f"severity = ${param_idx}")
            params.append(severity)
            param_idx += 1
        
        if acknowledged is not None:
            conditions.append(f"acknowledged = ${param_idx}")
            params.append(acknowledged)
            param_idx += 1
        
        if start_time:
            conditions.append(f"timestamp >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"timestamp <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        query = f"""
            SELECT * FROM monitoring_alerts
            WHERE {' AND '.join(conditions)}
            ORDER BY timestamp DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])
        
        rows = await db.fetch_all(query, *params)
        return [MonitoringRepository._row_to_alert(row) for row in rows]
    
    @staticmethod
    async def acknowledge_alert(alert_id: int, acknowledged_by: str) -> bool:
        """Marcar alerta como reconocida"""
        db = get_db()
        
        query = """
            UPDATE monitoring_alerts
            SET acknowledged = true, acknowledged_at = NOW(), acknowledged_by = $1
            WHERE id = $2
        """
        
        try:
            await db.execute(query, acknowledged_by, alert_id)
            return True
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False
    
    @staticmethod
    async def get_active_alerts_count() -> Dict[str, int]:
        """Obtener conteo de alertas activas por severidad"""
        db = get_db()
        
        query = """
            SELECT severity, COUNT(*) as count
            FROM monitoring_alerts
            WHERE acknowledged = false
            GROUP BY severity
        """
        
        rows = await db.fetch_all(query)
        
        counts = {"total": 0, "info": 0, "warning": 0, "critical": 0}
        for row in rows:
            counts[row['severity']] = row['count']
            counts["total"] += row['count']
        
        return counts
    
    # ============================================
    # Dashboard Stats
    # ============================================
    
    @staticmethod
    async def get_realtime_stats() -> Dict[str, Any]:
        """Obtener estadísticas en tiempo real (último minuto)"""
        db = get_db()
        
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        
        query = """
            SELECT 
                COUNT(*) as request_count,
                AVG(latency_ms) as avg_latency_ms,
                COUNT(*) FILTER (WHERE status_code >= 500) as error_count
            FROM api_metrics
            WHERE timestamp >= $1
        """
        
        row = await db.fetch_one(query, one_minute_ago)
        
        request_count = row['request_count'] or 0
        error_count = row['error_count'] or 0
        
        return {
            "requests_per_minute": request_count,
            "avg_latency_ms": row['avg_latency_ms'] or 0.0,
            "error_rate": error_count / request_count if request_count > 0 else 0.0
        }
    
    @staticmethod
    async def get_top_endpoints(limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener endpoints más usados (últimas 24h)"""
        db = get_db()
        
        query = """
            SELECT 
                endpoint,
                COUNT(*) as request_count,
                AVG(latency_ms) as avg_latency_ms,
                COUNT(*) FILTER (WHERE status_code >= 500) as error_count
            FROM api_metrics
            WHERE timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY endpoint
            ORDER BY request_count DESC
            LIMIT $1
        """
        
        rows = await db.fetch_all(query, limit)
        
        return [
            {
                "endpoint": row['endpoint'],
                "request_count": row['request_count'],
                "avg_latency_ms": row['avg_latency_ms'] or 0.0,
                "error_count": row['error_count'] or 0
            }
            for row in rows
        ]
    
    @staticmethod
    async def get_hourly_data(hours: int = 24) -> List[Dict[str, Any]]:
        """Obtener datos por hora"""
        db = get_db()
        
        query = """
            SELECT 
                date_trunc('hour', timestamp) as hour,
                COUNT(*) as request_count,
                AVG(latency_ms) as avg_latency_ms,
                COUNT(*) FILTER (WHERE status_code >= 500) as error_count
            FROM api_metrics
            WHERE timestamp >= NOW() - ($1 || ' hours')::interval
            GROUP BY date_trunc('hour', timestamp)
            ORDER BY hour ASC
        """
        
        rows = await db.fetch_all(query, str(hours))
        
        return [
            {
                "hour": row['hour'].isoformat() if row['hour'] else None,
                "request_count": row['request_count'] or 0,
                "avg_latency_ms": row['avg_latency_ms'] or 0.0,
                "error_count": row['error_count'] or 0
            }
            for row in rows
        ]
    
    # ============================================
    # Helper methods
    # ============================================
    
    @staticmethod
    def _row_to_metric(row) -> ApiMetric:
        return ApiMetric(
            id=row['id'],
            timestamp=row['timestamp'],
            endpoint=row['endpoint'],
            method=row['method'],
            status_code=row['status_code'],
            latency_ms=row['latency_ms'],
            request_size=row.get('request_size'),
            response_size=row.get('response_size'),
            user_id=row.get('user_id'),
            error_message=row.get('error_message'),
            metadata=row.get('metadata')
        )
    
    @staticmethod
    def _row_to_trace(row) -> ExecutionTrace:
        return ExecutionTrace(
            id=row['id'],
            execution_id=row['execution_id'],
            timestamp=row['timestamp'],
            chain_id=row.get('chain_id'),
            event_type=row['event_type'],
            node_id=row.get('node_id'),
            duration_ms=row.get('duration_ms'),
            tokens_input=row.get('tokens_input'),
            tokens_output=row.get('tokens_output'),
            cost_usd=row.get('cost_usd'),
            provider=row.get('provider'),
            model=row.get('model'),
            success=row.get('success'),
            error_message=row.get('error_message'),
            metadata=row.get('metadata')
        )
    
    @staticmethod
    def _row_to_alert(row) -> MonitoringAlert:
        # Parse metadata from JSON string to dict if necessary
        metadata = row.get('metadata')
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = None
        
        return MonitoringAlert(
            id=row['id'],
            timestamp=row['timestamp'],
            alert_type=row['alert_type'],
            severity=row['severity'],
            message=row['message'],
            metadata=metadata,
            acknowledged=row['acknowledged'],
            acknowledged_at=row.get('acknowledged_at'),
            acknowledged_by=row.get('acknowledged_by')
        )
