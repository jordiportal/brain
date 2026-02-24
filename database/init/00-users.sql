-- ===========================================
-- Brain Users + Role Permissions
-- Replaces legacy admin_users table
-- Default credentials: admin@brain.local / admin
-- CHANGE THE PASSWORD after first login!
-- ===========================================

-- Main users table
CREATE TABLE IF NOT EXISTS brain_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    firstname VARCHAR(255),
    lastname VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMPTZ,
    avatar_url VARCHAR(500),
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brain_users_email ON brain_users(email);
CREATE INDEX IF NOT EXISTS idx_brain_users_role ON brain_users(role);

-- Configurable permissions per role
CREATE TABLE IF NOT EXISTS brain_role_permissions (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    actions TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(role, resource)
);

-- Migrate data from admin_users if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'admin_users') THEN
        INSERT INTO brain_users (id, email, password, firstname, lastname, role, is_active, created_at, updated_at)
        SELECT id, email, password, firstname, lastname, 'admin', is_active, created_at, updated_at
        FROM admin_users
        ON CONFLICT (email) DO NOTHING;
    END IF;
END $$;

-- Seed default admin (only if no users exist)
INSERT INTO brain_users (firstname, lastname, email, password, role, is_active)
SELECT 'Admin', 'Brain', 'admin@brain.local',
       '$2b$12$ausxACT6VJjfJ9iLABc3weopU6FWJmffgC1LhoXoSm4.kneQ4rh16',
       'admin', true
WHERE NOT EXISTS (SELECT 1 FROM brain_users WHERE role = 'admin');

-- Fix serial sequence after migration
SELECT setval('brain_users_id_seq', COALESCE((SELECT MAX(id) FROM brain_users), 0));

-- Seed default role permissions
-- admin: full access to everything
INSERT INTO brain_role_permissions (role, resource, actions) VALUES
    ('admin', '*', '{read,write,delete,admin}')
ON CONFLICT (role, resource) DO NOTHING;

-- user: standard access
INSERT INTO brain_role_permissions (role, resource, actions) VALUES
    ('user', 'dashboard', '{read}'),
    ('user', 'profile', '{read,write}'),
    ('user', 'chat', '{read,write}'),
    ('user', 'testing', '{read,write}'),
    ('user', 'chains', '{read}'),
    ('user', 'subagents', '{read}'),
    ('user', 'tools', '{read}'),
    ('user', 'rag', '{read,write}'),
    ('user', 'monitoring', '{read}'),
    ('user', 'sandbox', '{read,write}'),
    ('user', 'artifacts', '{read,write}'),
    ('user', 'tasks', '{read,write}')
ON CONFLICT (role, resource) DO NOTHING;

-- viewer: read-only access
INSERT INTO brain_role_permissions (role, resource, actions) VALUES
    ('viewer', 'dashboard', '{read}'),
    ('viewer', 'profile', '{read}'),
    ('viewer', 'chains', '{read}'),
    ('viewer', 'subagents', '{read}'),
    ('viewer', 'tools', '{read}'),
    ('viewer', 'monitoring', '{read}'),
    ('viewer', 'artifacts', '{read}')
ON CONFLICT (role, resource) DO NOTHING;
