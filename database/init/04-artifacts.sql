-- ============================================
-- Artefactos - Gestión de archivos generados
-- ============================================

-- Tabla principal de artefactos
CREATE TABLE IF NOT EXISTS artifacts (
    id SERIAL PRIMARY KEY,
    artifact_id VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('image', 'video', 'presentation', 'code', 'document', 'html', 'audio', 'file', 'spreadsheet')),
    title VARCHAR(255),
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    
    -- Relaciones
    conversation_id VARCHAR(255),
    agent_id VARCHAR(100),
    user_id INTEGER,  -- Para futuro multi-usuario
    
    -- Origen
    source VARCHAR(50) NOT NULL DEFAULT 'tool_execution' CHECK (source IN ('tool_execution', 'user_upload', 'code_execution', 'imported')),
    tool_id VARCHAR(100), -- Tool que lo generó (generate_image, etc.)
    
    -- Metadata específica por tipo
    metadata JSONB DEFAULT '{}',
    -- Ejemplos:
    -- image: {width, height, format}
    -- video: {duration, resolution, codec, fps}
    -- presentation: {slides_count, theme}
    -- document: {pages, author}
    -- spreadsheet: {sheets_count, rows_count, columns_count, file_format}
    
    -- Versionado
    parent_artifact_id INTEGER REFERENCES artifacts(id) ON DELETE SET NULL,
    version INTEGER DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,
    
    -- Estado
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices optimizados
CREATE INDEX IF NOT EXISTS idx_artifacts_conversation ON artifacts(conversation_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);
CREATE INDEX IF NOT EXISTS idx_artifacts_agent ON artifacts(agent_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_created ON artifacts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifacts_status ON artifacts(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_artifacts_latest ON artifacts(is_latest, type) WHERE is_latest = TRUE;

-- Tabla de tags para categorización
CREATE TABLE IF NOT EXISTS artifact_tags (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(artifact_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_artifact_tags_tag ON artifact_tags(tag);
CREATE INDEX IF NOT EXISTS idx_artifact_tags_artifact ON artifact_tags(artifact_id);

-- Nota: El campo accessed_at se actualiza manualmente en el código
-- Los triggers en PostgreSQL no soportan BEFORE SELECT
-- La función Repository.get_by_id() actualiza este campo automáticamente

-- Función para marcar versiones anteriores como no-latest
CREATE OR REPLACE FUNCTION update_artifact_versioning()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.parent_artifact_id IS NOT NULL THEN
        -- Desmarcar versiones anteriores como no-latest
        UPDATE artifacts 
        SET is_latest = FALSE 
        WHERE parent_artifact_id = NEW.parent_artifact_id 
        AND id != NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para versionado
CREATE TRIGGER trigger_artifact_versioning
    AFTER INSERT ON artifacts
    FOR EACH ROW
    WHEN (NEW.parent_artifact_id IS NOT NULL)
    EXECUTE FUNCTION update_artifact_versioning();

-- Vista para artefactos activos con metadata enriquecida
CREATE OR REPLACE VIEW artifacts_enriched AS
SELECT 
    a.*,
    CASE 
        WHEN a.type = 'image' THEN 
            jsonb_build_object(
                'thumbnail_path', regexp_replace(a.file_path, '\.[^.]+$', '_thumb.jpg')
            )
        ELSE '{}'::jsonb
    END as enriched_metadata
FROM artifacts a
WHERE a.status = 'active';

COMMENT ON TABLE artifacts IS 'Almacena metadatos de archivos generados por tools y agentes';
COMMENT ON COLUMN artifacts.artifact_id IS 'ID único generado (ej: img_abc123, vid_xyz789)';
COMMENT ON COLUMN artifacts.type IS 'Tipo: image, video, presentation, code, document, html, audio, file';
COMMENT ON COLUMN artifacts.source IS 'Origen: tool_execution (generado por tool), user_upload (subido), code_execution (generado por código), imported (importado)';
