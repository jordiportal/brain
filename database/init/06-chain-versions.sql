-- ===========================================
-- Chain Versions (historial de asistentes)
-- ===========================================

CREATE TABLE IF NOT EXISTS chain_versions (
    id SERIAL PRIMARY KEY,
    brain_chain_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    snapshot JSONB NOT NULL,
    changed_by VARCHAR(255),
    change_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS chain_versions_chain_id_idx
    ON chain_versions (brain_chain_id);

CREATE UNIQUE INDEX IF NOT EXISTS chain_versions_chain_version_idx
    ON chain_versions (brain_chain_id, version_number);
