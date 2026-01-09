-- PostgreSQL initialization script for Multi-Agent Orchestration Platform
-- This script runs on container first startup

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE agent_type AS ENUM ('orchestrator', 'worker', 'specialist', 'research', 'analysis', 'coordinator');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE agent_status AS ENUM ('idle', 'busy', 'offline', 'failed', 'starting', 'stopping');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE task_status AS ENUM ('pending', 'queued', 'in_progress', 'completed', 'failed', 'cancelled', 'retrying');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE memory_type AS ENUM ('conversation', 'knowledge', 'context', 'short_term', 'mid_term', 'long_term');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'idle',
    capabilities JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',
    parent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_heartbeat TIMESTAMP WITH TIME ZONE,

    CONSTRAINT agents_name_not_empty CHECK (name <> '')
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    parent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 0 CHECK (priority >= -10 AND priority <= 10),
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    deadline TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT tasks_description_not_empty CHECK (description <> '')
);

-- Agent memory table with vector embeddings
CREATE TABLE IF NOT EXISTS agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI Ada-002 / Anthropic embeddings dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT memory_content_not_empty CHECK (content <> '')
);

-- Agent events for audit trail
CREATE TABLE IF NOT EXISTS agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    payload JSONB DEFAULT '{}',
    trace_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Task dependencies for DAG-based execution
CREATE TABLE IF NOT EXISTS task_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE NOT NULL,
    depends_on_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(task_id, depends_on_task_id),
    CHECK (task_id <> depends_on_task_id)
);

-- Agent pools for grouping and load balancing
CREATE TABLE IF NOT EXISTS agent_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    agent_type VARCHAR(50) NOT NULL,
    min_agents INTEGER DEFAULT 1 CHECK (min_agents >= 0),
    max_agents INTEGER DEFAULT 10 CHECK (max_agents >= 1),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent pool membership
CREATE TABLE IF NOT EXISTS agent_pool_membership (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE NOT NULL,
    pool_id UUID REFERENCES agent_pools(id) ON DELETE CASCADE NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(agent_id, pool_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(type);
CREATE INDEX IF NOT EXISTS idx_agents_parent ON agents(parent_id);
CREATE INDEX IF NOT EXISTS idx_agents_last_heartbeat ON agents(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_agents_capabilities ON agents USING gin(capabilities);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline) WHERE deadline IS NOT NULL;

-- Vector similarity search index using IVFFlat
CREATE INDEX IF NOT EXISTS idx_agent_memory_embedding ON agent_memory
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON agent_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_agent_memory_expires ON agent_memory(expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_agent_events_type ON agent_events(event_type);
CREATE INDEX IF NOT EXISTS idx_agent_events_agent ON agent_events(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_task ON agent_events(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_trace ON agent_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_created ON agent_events(created_at);

CREATE INDEX IF NOT EXISTS idx_task_deps_task ON task_dependencies(task_id);
CREATE INDEX IF NOT EXISTS idx_task_deps_depends ON task_dependencies(depends_on_task_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;
CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_pools_updated_at ON agent_pools;
CREATE TRIGGER update_agent_pools_updated_at
    BEFORE UPDATE ON agent_pools
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function for vector similarity search
CREATE OR REPLACE FUNCTION search_agent_memory(
    search_embedding vector(1536),
    search_agent_id UUID DEFAULT NULL,
    search_memory_type VARCHAR(50) DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.7,
    result_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    memory_id UUID,
    agent_id UUID,
    memory_type VARCHAR(50),
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        am.id,
        am.agent_id,
        am.memory_type,
        am.content,
        am.metadata,
        1 - (am.embedding <=> search_embedding) as similarity,
        am.created_at
    FROM agent_memory am
    WHERE
        (search_agent_id IS NULL OR am.agent_id = search_agent_id)
        AND (search_memory_type IS NULL OR am.memory_type = search_memory_type)
        AND am.embedding IS NOT NULL
        AND (am.expires_at IS NULL OR am.expires_at > NOW())
        AND 1 - (am.embedding <=> search_embedding) >= similarity_threshold
    ORDER BY am.embedding <=> search_embedding
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Create function to clean up expired memories
CREATE OR REPLACE FUNCTION cleanup_expired_memories()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM agent_memory WHERE expires_at IS NOT NULL AND expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to get task dependency graph
CREATE OR REPLACE FUNCTION get_task_dependencies(root_task_id UUID)
RETURNS TABLE (
    task_id UUID,
    depends_on_task_id UUID,
    task_status VARCHAR(50),
    depth INTEGER
) AS $$
WITH RECURSIVE deps AS (
    -- Base case: direct dependencies
    SELECT
        td.task_id,
        td.depends_on_task_id,
        t.status,
        1 as depth
    FROM task_dependencies td
    JOIN tasks t ON t.id = td.depends_on_task_id
    WHERE td.task_id = root_task_id

    UNION ALL

    -- Recursive case: dependencies of dependencies
    SELECT
        td.task_id,
        td.depends_on_task_id,
        t.status,
        d.depth + 1
    FROM task_dependencies td
    JOIN deps d ON td.task_id = d.depends_on_task_id
    JOIN tasks t ON t.id = td.depends_on_task_id
    WHERE d.depth < 10  -- Prevent infinite recursion
)
SELECT * FROM deps;
$$ LANGUAGE sql;

-- Insert default agent pools
INSERT INTO agent_pools (name, description, agent_type, min_agents, max_agents) VALUES
    ('research-pool', 'Pool for research-oriented agents', 'research', 2, 10),
    ('analysis-pool', 'Pool for data analysis agents', 'analysis', 2, 10),
    ('worker-pool', 'General purpose worker agents', 'worker', 5, 50),
    ('coordinator-pool', 'Coordinator agents for task delegation', 'coordinator', 1, 5)
ON CONFLICT (name) DO NOTHING;

-- Grant permissions (adjust as needed for your security requirements)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agent_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agent_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO agent_user;
