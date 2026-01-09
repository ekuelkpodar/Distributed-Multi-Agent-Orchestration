import { useQuery } from '@tanstack/react-query';
import { systemApi } from '../api/systemApi';

// Query keys
export const systemKeys = {
  all: ['system'] as const,
  health: () => [...systemKeys.all, 'health'] as const,
  metrics: () => [...systemKeys.all, 'metrics'] as const,
  events: (filters?: Record<string, unknown>) => [...systemKeys.all, 'events', filters] as const,
};

// Health check hook
export function useHealth() {
  return useQuery({
    queryKey: systemKeys.health(),
    queryFn: () => systemApi.health(),
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: 1,
  });
}

// System metrics hook
export function useMetrics() {
  return useQuery({
    queryKey: systemKeys.metrics(),
    queryFn: () => systemApi.metrics(),
    refetchInterval: 5000, // Refresh every 5 seconds
  });
}

// System events hook
export function useEvents(params?: { limit?: number; offset?: number; type?: string }) {
  return useQuery({
    queryKey: systemKeys.events(params),
    queryFn: () => systemApi.events(params),
    refetchInterval: 3000, // Refresh every 3 seconds
  });
}
