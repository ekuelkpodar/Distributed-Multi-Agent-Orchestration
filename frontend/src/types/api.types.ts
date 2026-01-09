// Agent types
export type AgentStatus = 'active' | 'idle' | 'busy' | 'offline' | 'failed' | 'starting';
export type AgentType = 'orchestrator' | 'worker' | 'specialist' | 'research' | 'analysis' | 'coordinator';

export interface AgentCapabilities {
  skills: string[];
  max_concurrent_tasks: number;
  supported_task_types: string[];
  tools: string[];
}

export interface AgentConfig {
  model: string;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
  retry_attempts: number;
  memory_enabled: boolean;
}

export interface Agent {
  id: string;
  name: string;
  type: AgentType;
  status: AgentStatus;
  capabilities: AgentCapabilities;
  config: AgentConfig;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
  last_heartbeat: string;
}

export interface AgentListResponse {
  agents: Agent[];
  total: number;
  page: number;
  page_size: number;
}

export interface SpawnAgentRequest {
  name: string;
  agent_type: AgentType;
  model?: string;
  capabilities?: string[];
}

export interface SpawnAgentResponse {
  agent_id: string;
  name: string;
  status: string;
  message: string;
}

// Task types
export type TaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
export type TaskPriority = 1 | 2 | 3 | 4 | 5;

export interface Task {
  id: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  agent_id: string | null;
  parent_task_id: string | null;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  page: number;
  page_size: number;
}

export interface SubmitTaskRequest {
  description: string;
  priority?: TaskPriority;
  agent_id?: string;
  input_data?: Record<string, unknown>;
}

export interface SubmitTaskResponse {
  task_id: string;
  status: string;
  assigned_agent: string | null;
  message: string;
}

// Health and system types
export interface ComponentHealth {
  status: 'healthy' | 'unhealthy' | 'degraded';
  database?: string;
  version?: string;
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  version: string;
  components: {
    database: ComponentHealth;
    redis: ComponentHealth;
  };
}

// Metrics types
export interface SystemMetrics {
  active_agents: number;
  total_agents: number;
  pending_tasks: number;
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  avg_task_duration_ms: number;
  tasks_per_second: number;
  cpu_usage: number;
  memory_usage: number;
}

// Event types
export type EventType =
  | 'agent.spawned'
  | 'agent.started'
  | 'agent.stopped'
  | 'agent.heartbeat'
  | 'task.assigned'
  | 'task.started'
  | 'task.progress'
  | 'task.completed'
  | 'task.failed'
  | 'system.alert';

export interface SystemEvent {
  id: string;
  type: EventType;
  timestamp: string;
  severity: 'info' | 'success' | 'warning' | 'error';
  message: string;
  metadata?: Record<string, unknown>;
  agent_id?: string;
  task_id?: string;
}
