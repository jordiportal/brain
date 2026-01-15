-- ===========================================
-- Brain Database Initialization
-- PostgreSQL + pgvector
-- ===========================================
-- NOTA: Las tablas de gestión (chains, executions, settings, etc.)
-- son gestionadas por Strapi. Este script solo inicializa
-- las extensiones y tablas específicas de RAG/vectores.

-- Habilitar extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Habilitar extensión uuid-ossp para generación de UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- Tabla de documentos para RAG (pgvector)
-- Esta tabla es gestionada directamente por la API Python
-- para operaciones de RAG con embeddings vectoriales
-- ===========================================

CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection VARCHAR(255) NOT NULL DEFAULT 'default',
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(768),  -- Dimensión para nomic-embed-text
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índice para búsqueda vectorial (IVFFlat para mejor rendimiento)
-- Nota: Este índice requiere al menos 100 documentos para ser efectivo
CREATE INDEX IF NOT EXISTS rag_documents_embedding_idx 
ON rag_documents USING hnsw (embedding vector_cosine_ops);

-- Índice para filtrar por colección
CREATE INDEX IF NOT EXISTS rag_documents_collection_idx 
ON rag_documents (collection);

-- Índice GIN para búsqueda en metadata
CREATE INDEX IF NOT EXISTS rag_documents_metadata_idx 
ON rag_documents USING GIN (metadata);

-- ===========================================
-- Función para actualizar updated_at
-- ===========================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para auto-actualizar updated_at
DROP TRIGGER IF EXISTS update_rag_documents_updated_at ON rag_documents;
CREATE TRIGGER update_rag_documents_updated_at
    BEFORE UPDATE ON rag_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- Mensaje de confirmación
-- ===========================================
DO $$
BEGIN
    RAISE NOTICE 'Brain database initialized successfully with pgvector extension';
    RAISE NOTICE 'RAG documents table created. Strapi will manage other entities.';
END $$;
