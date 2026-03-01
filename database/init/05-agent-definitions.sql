-- ===========================================
-- Agent Definitions + Version History
-- ===========================================

CREATE TABLE IF NOT EXISTS agent_definitions (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    role VARCHAR(500),
    expertise TEXT,
    task_requirements TEXT,
    system_prompt TEXT NOT NULL,
    domain_tools TEXT[] DEFAULT '{}',
    core_tools_enabled BOOLEAN DEFAULT TRUE,
    excluded_core_tools TEXT[] DEFAULT '{}',
    skills JSONB DEFAULT '[]',
    is_enabled BOOLEAN DEFAULT TRUE,
    version VARCHAR(50) DEFAULT '1.0.0',
    icon VARCHAR(100),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_definitions_agent_id ON agent_definitions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_definitions_enabled ON agent_definitions(is_enabled);

CREATE TABLE IF NOT EXISTS agent_versions (
    id SERIAL PRIMARY KEY,
    agent_definition_id INTEGER NOT NULL REFERENCES agent_definitions(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    snapshot JSONB NOT NULL,
    changed_by VARCHAR(255),
    change_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_versions_def_id
    ON agent_versions(agent_definition_id, version_number DESC);
