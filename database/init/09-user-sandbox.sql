-- ============================================
-- User Sandbox: perfiles y tareas programadas
-- ============================================
-- Tablas: user_profiles, user_tasks, user_task_results, user_task_run_now
-- ============================================

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255),
    personal_prompt TEXT,
    m365_user_id VARCHAR(255),
    timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Madrid',
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_tasks (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    type VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    cron_expression VARCHAR(128) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    config JSONB NOT NULL DEFAULT '{}',
    llm_provider_id INTEGER,
    llm_model VARCHAR(128),
    last_run_at TIMESTAMPTZ,
    last_status VARCHAR(32),
    next_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_tasks_user_id ON user_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tasks_active ON user_tasks(is_active) WHERE is_active = true;

CREATE TABLE IF NOT EXISTS user_task_results (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES user_tasks(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    result_type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    is_read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days')
);

CREATE INDEX IF NOT EXISTS idx_task_results_user_unread ON user_task_results(user_id, is_read)
    WHERE is_read = false;
CREATE INDEX IF NOT EXISTS idx_task_results_expires ON user_task_results(expires_at);

CREATE TABLE IF NOT EXISTS user_task_run_now (
    task_id INTEGER NOT NULL PRIMARY KEY REFERENCES user_tasks(id) ON DELETE CASCADE,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Triggers updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_profiles_updated_at ON user_profiles;
CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at();

DROP TRIGGER IF EXISTS user_tasks_updated_at ON user_tasks;
CREATE TRIGGER user_tasks_updated_at
    BEFORE UPDATE ON user_tasks
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at();

-- Seed
INSERT INTO user_profiles (user_id, display_name, timezone, preferences)
VALUES (
    'jordip@khlloreda.com',
    'Jordi',
    'Europe/Madrid',
    '{"importantSenders": [], "projectKeywords": [], "digestFormat": "bullet"}'::jsonb
) ON CONFLICT (user_id) DO NOTHING;

INSERT INTO user_tasks (user_id, type, name, cron_expression, is_active, config)
SELECT 'jordip@khlloreda.com', 'mail_digest', 'Resumen de correo', '0 8 * * 1-5', false, '{}'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM user_tasks WHERE user_id = 'jordip@khlloreda.com' AND type = 'mail_digest'
);
