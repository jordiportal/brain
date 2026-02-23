-- ===========================================
-- Brain Settings - Configuración general del sistema
-- Tabla key-value para settings configurables desde el GUI
-- ===========================================

CREATE TABLE IF NOT EXISTS brain_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'number',   -- number | string | boolean | json
    category VARCHAR(50) NOT NULL DEFAULT 'general', -- general | security | llm | rag
    label VARCHAR(200),
    description TEXT,
    is_public BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- Seed: valores por defecto
-- ===========================================

INSERT INTO brain_settings (key, value, type, category, label, description) VALUES
(
    'tool_result_max_chars',
    '100000'::jsonb,
    'number',
    'general',
    'Límite de caracteres por resultado de tool',
    'Máximo de caracteres que se pasan al LLM por cada resultado de herramienta. Aumenta para modelos con contexto grande (Claude, GPT-4o, Gemini). Reduce a 16000–32000 si usas modelos Ollama pequeños con contexto limitado.'
)
ON CONFLICT (key) DO NOTHING;

INSERT INTO brain_settings (key, value, type, category, label, description) VALUES
(
    'oauth_enabled',
    'false'::jsonb,
    'boolean',
    'security',
    'Activar autenticación OAuth / Microsoft Entra ID',
    'Permite autenticar usuarios mediante tokens JWT de Microsoft Entra ID (Azure AD) además de API keys. Requiere configurar Tenant ID y Client ID.'
)
ON CONFLICT (key) DO NOTHING;

INSERT INTO brain_settings (key, value, type, category, label, description) VALUES
(
    'oauth_azure_tenant_id',
    '""'::jsonb,
    'string',
    'security',
    'Azure AD Tenant ID',
    'ID del tenant de Microsoft Entra ID. Se encuentra en Azure Portal > App Registrations > Overview. Formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
)
ON CONFLICT (key) DO NOTHING;

INSERT INTO brain_settings (key, value, type, category, label, description) VALUES
(
    'oauth_azure_client_id',
    '""'::jsonb,
    'string',
    'security',
    'Azure AD Client ID (Application ID)',
    'Application (client) ID del app registration en Entra ID. Se usa como audience para validar los JWT. Normalmente es el Client ID de OpenWebUI.'
)
ON CONFLICT (key) DO NOTHING;

INSERT INTO brain_settings (key, value, type, category, label, description) VALUES
(
    'oauth_allowed_models',
    '"*"'::jsonb,
    'string',
    'security',
    'Modelos permitidos para usuarios OAuth',
    'Lista de modelos accesibles por usuarios autenticados via OAuth. Usa * para todos, o una lista separada por comas: brain-adaptive, brain-creative. Se aplica a todos los usuarios OAuth.'
)
ON CONFLICT (key) DO NOTHING;
