-- ============================================
-- Conversations: Brain as source of truth
-- ============================================

CREATE TABLE IF NOT EXISTS conversations (
    id          VARCHAR(255) PRIMARY KEY,
    user_id     VARCHAR(255) NOT NULL,
    title       TEXT,
    chain_id    VARCHAR(255),
    model       VARCHAR(255),
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_user_updated ON conversations(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id                VARCHAR(255) PRIMARY KEY,
    conversation_id   VARCHAR(255) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role              VARCHAR(50) NOT NULL,
    content           TEXT NOT NULL DEFAULT '',
    parts             JSONB,
    model             VARCHAR(255),
    tokens_used       INTEGER DEFAULT 0,
    task_id           VARCHAR(255),
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cmsg_conv ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_cmsg_conv_created ON conversation_messages(conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_cmsg_task ON conversation_messages(task_id);
