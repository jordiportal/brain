-- ===========================================
-- Subagent Configs Table
-- ===========================================

-- Tabla para almacenar configuración de subagentes (LLM provider, modelo, settings)
CREATE TABLE IF NOT EXISTS subagent_configs (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL UNIQUE,  -- designer_agent, researcher_agent, etc.
    is_enabled BOOLEAN DEFAULT TRUE,
    llm_provider_id INTEGER REFERENCES brain_llm_providers(id) ON DELETE SET NULL,
    llm_model VARCHAR(255),  -- Override del modelo (NULL = usar default del provider)
    system_prompt TEXT,  -- Override del prompt del sistema
    settings JSONB,  -- Configuraciones adicionales del subagente
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índice para búsqueda rápida por agent_id
CREATE INDEX IF NOT EXISTS idx_subagent_configs_agent_id ON subagent_configs(agent_id);

-- Comentarios
COMMENT ON TABLE subagent_configs IS 'Configuración de subagentes (LLM, modelo, settings)';
COMMENT ON COLUMN subagent_configs.agent_id IS 'ID único del subagente (ej: designer_agent)';
COMMENT ON COLUMN subagent_configs.is_enabled IS 'Si el subagente está habilitado';
COMMENT ON COLUMN subagent_configs.llm_provider_id IS 'FK al proveedor LLM a usar';
COMMENT ON COLUMN subagent_configs.llm_model IS 'Modelo específico (override del default del provider)';
COMMENT ON COLUMN subagent_configs.system_prompt IS 'System prompt personalizado';
COMMENT ON COLUMN subagent_configs.settings IS 'Configuraciones adicionales en JSON';
