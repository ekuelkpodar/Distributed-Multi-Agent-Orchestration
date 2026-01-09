import { get, post, patch, del } from '@/lib/api/axios';
import type {
  Agent,
  AgentListResponse,
  SpawnAgentRequest,
  SpawnAgentResponse,
} from '@/types/api.types';

export const agentsApi = {
  // List all agents
  list: async (params?: { page?: number; page_size?: number; status?: string; type?: string }) => {
    return get<AgentListResponse>('/api/v1/agents', { params });
  },

  // Get agent by ID
  get: async (agentId: string) => {
    return get<Agent>(`/api/v1/agents/${agentId}`);
  },

  // Spawn a new agent
  spawn: async (data: SpawnAgentRequest) => {
    return post<SpawnAgentResponse>('/api/v1/agents/spawn', data);
  },

  // Update agent status
  updateStatus: async (agentId: string, status: string) => {
    return patch<{ status: string; agent_id: string; new_status: string }>(
      `/api/v1/agents/${agentId}/status?status=${status}`
    );
  },

  // Terminate agent
  terminate: async (agentId: string) => {
    return del<{ message: string }>(`/api/v1/agents/${agentId}`);
  },
};
