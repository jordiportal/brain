-- ===========================================
-- Core tables (previously managed by Strapi)
-- Must run BEFORE 03+ scripts that reference these
-- ===========================================

-- LLM Providers
CREATE TABLE IF NOT EXISTS brain_llm_providers (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255),
    name VARCHAR(255),
    type VARCHAR(50),
    base_url TEXT,
    api_key TEXT,
    default_model VARCHAR(255),
    embedding_model VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    config JSONB DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- Alias view for FK references using short name
CREATE OR REPLACE VIEW llm_providers AS SELECT * FROM brain_llm_providers;

-- Brain Chains (assistants)
CREATE TABLE IF NOT EXISTS brain_chains (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255),
    slug VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    type VARCHAR(50),
    description TEXT,
    version VARCHAR(50),
    handler_type VARCHAR(50),
    definition JSONB,
    prompts JSONB DEFAULT '{}',
    tools JSONB DEFAULT '[]',
    nodes JSONB DEFAULT '[]',
    edges JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    tags TEXT[],
    is_active BOOLEAN DEFAULT true,
    legacy_builder_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- Chain <-> LLM Provider link
CREATE TABLE IF NOT EXISTS brain_chains_llm_provider_lnk (
    id SERIAL PRIMARY KEY,
    brain_chain_id INTEGER REFERENCES brain_chains(id) ON DELETE CASCADE,
    brain_llm_provider_id INTEGER REFERENCES brain_llm_providers(id) ON DELETE CASCADE
);

-- API Keys
CREATE TABLE IF NOT EXISTS brain_api_keys (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255),
    name VARCHAR(255),
    key VARCHAR(255) UNIQUE,
    key_prefix VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    permissions JSONB DEFAULT '{}',
    usage_stats JSONB DEFAULT '{}',
    expires_at TIMESTAMPTZ,
    created_by_user VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- Model Configs
CREATE TABLE IF NOT EXISTS brain_model_configs (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255),
    is_enabled BOOLEAN DEFAULT false,
    base_url TEXT,
    default_model VARCHAR(255),
    available_models JSONB DEFAULT '[]',
    backend_llm JSONB DEFAULT '{}',
    rate_limits JSONB DEFAULT '{}',
    logging_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- OpenAPI Connections
CREATE TABLE IF NOT EXISTS openapi_connections (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255),
    name VARCHAR(255),
    slug VARCHAR(255) UNIQUE,
    description TEXT,
    spec_url TEXT,
    base_url TEXT,
    auth_type VARCHAR(50) DEFAULT 'none',
    auth_token TEXT,
    auth_header VARCHAR(255),
    auth_prefix VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    timeout INTEGER DEFAULT 30,
    enabled_endpoints JSONB DEFAULT '[]',
    custom_headers JSONB DEFAULT '{}',
    last_sync_at TIMESTAMPTZ,
    cached_spec JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- MCP Connections
CREATE TABLE IF NOT EXISTS mcp_connections (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255),
    name VARCHAR(255),
    type VARCHAR(50),
    command TEXT,
    args JSONB DEFAULT '[]',
    server_url TEXT,
    env JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    description TEXT,
    tools JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- Tool Configs
CREATE TABLE IF NOT EXISTS tool_configs (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    last_updated TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

-- Tool config component settings
CREATE TABLE IF NOT EXISTS components_tool_settings_executions (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES tool_configs(id) ON DELETE CASCADE,
    timeout INTEGER DEFAULT 30,
    memory_limit VARCHAR(50) DEFAULT '512m',
    cpu_limit VARCHAR(50) DEFAULT '1.0'
);

-- Code executions
CREATE TABLE IF NOT EXISTS code_executions (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255),
    code TEXT,
    language VARCHAR(50),
    execution_type VARCHAR(50),
    status VARCHAR(50),
    stdout TEXT,
    stderr TEXT,
    exit_code INTEGER,
    execution_time FLOAT,
    container_id VARCHAR(255),
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    published_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS code_executions_brain_chain_lnk (
    id SERIAL PRIMARY KEY,
    code_execution_id INTEGER REFERENCES code_executions(id) ON DELETE CASCADE,
    brain_chain_id INTEGER REFERENCES brain_chains(id) ON DELETE CASCADE
);

DO $$ BEGIN
    RAISE NOTICE 'Core tables created successfully';
END $$;
