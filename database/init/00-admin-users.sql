-- ===========================================
-- Admin users table + default admin user
-- Default credentials: admin@brain.local / admin
-- CHANGE THE PASSWORD after first login!
-- ===========================================

CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    firstname VARCHAR(255),
    lastname VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO admin_users (firstname, lastname, email, password, is_active)
VALUES ('Admin', 'Brain', 'admin@brain.local', '$2b$10$QRAuZZ/9Ay3sm5zcGKIIdONuflDpklWLiMV8zZxuw3KxVWh8u0u2y', true)
ON CONFLICT (email) DO NOTHING;
