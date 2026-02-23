-- ===========================================
-- User Sandboxes — Per-user Docker containers
-- Tracks sandbox lifecycle: create, start, stop, remove
-- ===========================================

CREATE TABLE IF NOT EXISTS user_sandboxes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL UNIQUE,
    container_name VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    resource_limits JSONB NOT NULL DEFAULT '{"memory": "256m", "cpus": "0.5"}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_sandboxes_user_id ON user_sandboxes(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sandboxes_status ON user_sandboxes(status);
