import { get } from '@/lib/api/axios';
import type { HealthResponse, SystemMetrics, SystemEvent } from '@/types/api.types';

export const systemApi = {
  // Get system health
  health: async () => {
    return get<HealthResponse>('/api/v1/health');
  },

  // Get system metrics
  metrics: async () => {
    return get<SystemMetrics>('/api/v1/metrics');
  },

  // Get recent events
  events: async (params?: { limit?: number; offset?: number; type?: string }) => {
    return get<{ events: SystemEvent[]; total: number }>('/api/v1/events', { params });
  },
};
