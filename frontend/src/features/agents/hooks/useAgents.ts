import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentsApi } from '../api/agentsApi';
import type { SpawnAgentRequest } from '@/types/api.types';

// Query keys
export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...agentKeys.lists(), filters] as const,
  details: () => [...agentKeys.all, 'detail'] as const,
  detail: (id: string) => [...agentKeys.details(), id] as const,
};

// List agents hook
export function useAgents(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  type?: string;
}) {
  return useQuery({
    queryKey: agentKeys.list(params || {}),
    queryFn: () => agentsApi.list(params),
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}

// Get single agent hook
export function useAgent(agentId: string) {
  return useQuery({
    queryKey: agentKeys.detail(agentId),
    queryFn: () => agentsApi.get(agentId),
    enabled: !!agentId,
    refetchInterval: 3000, // Refresh every 3 seconds for active agent
  });
}

// Spawn agent mutation
export function useSpawnAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SpawnAgentRequest) => agentsApi.spawn(data),
    onSuccess: () => {
      // Invalidate agents list to trigger refetch
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
    },
  });
}

// Update agent status mutation
export function useUpdateAgentStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ agentId, status }: { agentId: string; status: string }) =>
      agentsApi.updateStatus(agentId, status),
    onSuccess: (_, variables) => {
      // Invalidate specific agent and list
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(variables.agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
    },
  });
}

// Terminate agent mutation
export function useTerminateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentId: string) => agentsApi.terminate(agentId),
    onSuccess: (_, agentId) => {
      // Invalidate specific agent and list
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(agentId) });
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() });
    },
  });
}
