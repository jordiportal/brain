-- ============================================
-- Engine v2: Task-centric architecture
-- ============================================

-- Tasks: central unit of work with lifecycle
CREATE TABLE IF NOT EXISTS tasks (
    id              VARCHAR(255) PRIMARY KEY,
    context_id      VARCHAR(255) NOT NULL,
    parent_task_id  VARCHAR(255) REFERENCES tasks(id) ON DELETE SET NULL,
    agent_id        VARCHAR(255),
    chain_id        VARCHAR(255),

    state           VARCHAR(50) NOT NULL DEFAULT 'submitted',
    state_reason    TEXT,

    input           JSONB NOT NULL,
    output          JSONB,
    history         JSONB DEFAULT '[]',
    artifacts       JSONB DEFAULT '[]',

    checkpoint_thread_id VARCHAR(255),

    tokens_used     INTEGER DEFAULT 0,
    cost_usd        FLOAT DEFAULT 0.0,
    duration_ms     INTEGER DEFAULT 0,
    iterations      INTEGER DEFAULT 0,

    metadata        JSONB DEFAULT '{}',
    created_by      VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tasks_context ON tasks(context_id);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON tasks(created_by);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

-- Task events: audit trail of state transitions
CREATE TABLE IF NOT EXISTS task_events (
    id          SERIAL PRIMARY KEY,
    task_id     VARCHAR(255) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    state       VARCHAR(50) NOT NULL,
    reason      TEXT,
    message     JSONB,
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id);
CREATE INDEX IF NOT EXISTS idx_task_events_created ON task_events(created_at DESC);

-- Agent states: persistent typed state per agent+context
CREATE TABLE IF NOT EXISTS agent_states (
    agent_id    VARCHAR(255) NOT NULL,
    context_id  VARCHAR(255) NOT NULL,
    state       JSONB DEFAULT '{}',
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (agent_id, context_id)
);

-- Memory long-term: cross-session facts with embeddings
CREATE TABLE IF NOT EXISTS memory_long_term (
    id              SERIAL PRIMARY KEY,
    agent_id        VARCHAR(255),
    user_id         VARCHAR(255) NOT NULL,
    type            VARCHAR(50) NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(768),
    source_task_id  VARCHAR(255) REFERENCES tasks(id) ON DELETE SET NULL,
    relevance_score FLOAT DEFAULT 1.0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    accessed_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_lt_user ON memory_long_term(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_lt_agent_user ON memory_long_term(agent_id, user_id);

-- Memory episodes: auto-summarized past interactions
CREATE TABLE IF NOT EXISTS memory_episodes (
    id              SERIAL PRIMARY KEY,
    agent_id        VARCHAR(255),
    user_id         VARCHAR(255) NOT NULL,
    context_id      VARCHAR(255),
    summary         TEXT NOT NULL,
    key_points      JSONB DEFAULT '[]',
    task_ids        TEXT[] DEFAULT '{}',
    message_count   INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodes_user ON memory_episodes(user_id);
CREATE INDEX IF NOT EXISTS idx_episodes_agent_user ON memory_episodes(agent_id, user_id);

-- View: active tasks summary (for dashboard)
CREATE OR REPLACE VIEW active_tasks_summary AS
SELECT
    state,
    COUNT(*) as count,
    AVG(duration_ms) as avg_duration_ms,
    SUM(tokens_used) as total_tokens
FROM tasks
WHERE state IN ('submitted', 'working', 'input_required')
GROUP BY state;
