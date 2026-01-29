-- ============================================
-- Brain Monitoring Tables
-- ============================================

-- Métricas de API (requests, latencia, errores)
CREATE TABLE IF NOT EXISTS api_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INT,
    latency_ms FLOAT,
    request_size INT,
    response_size INT,
    user_id VARCHAR(100),
    error_message TEXT,
    metadata JSONB
);

-- Trazas de ejecución (chains, tools, LLM calls)
CREATE TABLE IF NOT EXISTS execution_traces (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(100),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    chain_id VARCHAR(100),
    event_type VARCHAR(50),  -- 'chain_start', 'tool_call', 'llm_call', 'chain_end'
    node_id VARCHAR(100),
    duration_ms FLOAT,
    tokens_input INT,
    tokens_output INT,
    cost_usd FLOAT,
    provider VARCHAR(50),
    model VARCHAR(100),
    success BOOLEAN,
    error_message TEXT,
    metadata JSONB
);

-- Alertas de monitorización
CREATE TABLE IF NOT EXISTS monitoring_alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    alert_type VARCHAR(50),  -- 'error_rate', 'latency', 'token_limit', 'cost'
    severity VARCHAR(20),    -- 'info', 'warning', 'critical'
    message TEXT,
    metadata JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100)
);

-- ============================================
-- Índices para consultas rápidas
-- ============================================

CREATE INDEX IF NOT EXISTS idx_api_metrics_timestamp ON api_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_metrics_endpoint ON api_metrics(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_metrics_status ON api_metrics(status_code);

CREATE INDEX IF NOT EXISTS idx_execution_traces_execution_id ON execution_traces(execution_id);
CREATE INDEX IF NOT EXISTS idx_execution_traces_timestamp ON execution_traces(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_execution_traces_chain_id ON execution_traces(chain_id);
CREATE INDEX IF NOT EXISTS idx_execution_traces_event_type ON execution_traces(event_type);

CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON monitoring_alerts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON monitoring_alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON monitoring_alerts(severity);

-- ============================================
-- Función para limpiar métricas antiguas (retention 30 días)
-- ============================================

CREATE OR REPLACE FUNCTION cleanup_old_metrics() RETURNS void AS $$
BEGIN
    DELETE FROM api_metrics WHERE timestamp < NOW() - INTERVAL '30 days';
    DELETE FROM execution_traces WHERE timestamp < NOW() - INTERVAL '30 days';
    DELETE FROM monitoring_alerts WHERE timestamp < NOW() - INTERVAL '90 days' AND acknowledged = true;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Vista para métricas agregadas por hora
-- ============================================

CREATE OR REPLACE VIEW hourly_metrics AS
SELECT 
    date_trunc('hour', timestamp) as hour,
    endpoint,
    COUNT(*) as request_count,
    AVG(latency_ms) as avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms,
    COUNT(*) FILTER (WHERE status_code >= 500) as error_count,
    COUNT(*) FILTER (WHERE status_code >= 200 AND status_code < 300) as success_count
FROM api_metrics
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY date_trunc('hour', timestamp), endpoint
ORDER BY hour DESC;

-- ============================================
-- Vista para estadísticas de ejecución por chain
-- ============================================

CREATE OR REPLACE VIEW chain_stats AS
SELECT 
    chain_id,
    date_trunc('day', timestamp) as day,
    COUNT(DISTINCT execution_id) as executions,
    AVG(duration_ms) FILTER (WHERE event_type = 'chain_end') as avg_duration_ms,
    SUM(tokens_input) as total_tokens_input,
    SUM(tokens_output) as total_tokens_output,
    SUM(cost_usd) as total_cost_usd,
    COUNT(*) FILTER (WHERE success = false) as error_count
FROM execution_traces
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY chain_id, date_trunc('day', timestamp)
ORDER BY day DESC, chain_id;
