import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksApi } from '../api/tasksApi';
import type { SubmitTaskRequest } from '@/types/api.types';

// Query keys
export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...taskKeys.lists(), filters] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
};

// List tasks hook
export function useTasks(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  agent_id?: string;
}) {
  return useQuery({
    queryKey: taskKeys.list(params || {}),
    queryFn: () => tasksApi.list(params),
    refetchInterval: 3000, // Refresh every 3 seconds
  });
}

// Get single task hook
export function useTask(taskId: string) {
  return useQuery({
    queryKey: taskKeys.detail(taskId),
    queryFn: () => tasksApi.get(taskId),
    enabled: !!taskId,
    refetchInterval: 2000, // Refresh every 2 seconds for active task
  });
}

// Submit task mutation
export function useSubmitTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SubmitTaskRequest) => tasksApi.submit(data),
    onSuccess: () => {
      // Invalidate tasks list to trigger refetch
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}

// Cancel task mutation
export function useCancelTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => tasksApi.cancel(taskId),
    onSuccess: (_, taskId) => {
      // Invalidate specific task and list
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}

// Delete task mutation
export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => tasksApi.delete(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}

// Retry task mutation
export function useRetryTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => tasksApi.retry(taskId),
    onSuccess: (_, taskId) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}
