import { get, post, patch, del } from '@/lib/api/axios';
import type {
  Task,
  TaskListResponse,
  SubmitTaskRequest,
  SubmitTaskResponse,
} from '@/types/api.types';

export const tasksApi = {
  // List all tasks
  list: async (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    agent_id?: string;
  }) => {
    return get<TaskListResponse>('/api/v1/tasks', { params });
  },

  // Get task by ID
  get: async (taskId: string) => {
    return get<Task>(`/api/v1/tasks/${taskId}`);
  },

  // Submit a new task
  submit: async (data: SubmitTaskRequest) => {
    return post<SubmitTaskResponse>('/api/v1/tasks', data);
  },

  // Cancel a task
  cancel: async (taskId: string) => {
    return patch<{ message: string; task_id: string }>(`/api/v1/tasks/${taskId}/cancel`);
  },

  // Delete a task
  delete: async (taskId: string) => {
    return del<{ message: string }>(`/api/v1/tasks/${taskId}`);
  },

  // Retry a failed task
  retry: async (taskId: string) => {
    return post<SubmitTaskResponse>(`/api/v1/tasks/${taskId}/retry`);
  },
};
