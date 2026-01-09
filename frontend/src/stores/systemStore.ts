import { create } from 'zustand';
import type { SystemEvent, Agent, Task } from '@/types/api.types';

interface SystemState {
  // Connection status
  isConnected: boolean;
  setConnected: (connected: boolean) => void;

  // Real-time events
  events: SystemEvent[];
  addEvent: (event: SystemEvent) => void;
  clearEvents: () => void;

  // Agent updates (from WebSocket)
  agentUpdates: Map<string, Partial<Agent>>;
  updateAgent: (agentId: string, update: Partial<Agent>) => void;
  clearAgentUpdate: (agentId: string) => void;

  // Task updates (from WebSocket)
  taskUpdates: Map<string, Partial<Task>>;
  updateTask: (taskId: string, update: Partial<Task>) => void;
  clearTaskUpdate: (taskId: string) => void;

  // Notifications
  notifications: Array<{
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    title: string;
    message: string;
    timestamp: string;
    read: boolean;
  }>;
  addNotification: (notification: Omit<SystemState['notifications'][0], 'id' | 'timestamp' | 'read'>) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  // Connection status
  isConnected: false,
  setConnected: (connected) => set({ isConnected: connected }),

  // Real-time events
  events: [],
  addEvent: (event) =>
    set((state) => ({
      events: [event, ...state.events].slice(0, 100), // Keep last 100 events
    })),
  clearEvents: () => set({ events: [] }),

  // Agent updates
  agentUpdates: new Map(),
  updateAgent: (agentId, update) =>
    set((state) => {
      const newUpdates = new Map(state.agentUpdates);
      newUpdates.set(agentId, { ...newUpdates.get(agentId), ...update });
      return { agentUpdates: newUpdates };
    }),
  clearAgentUpdate: (agentId) =>
    set((state) => {
      const newUpdates = new Map(state.agentUpdates);
      newUpdates.delete(agentId);
      return { agentUpdates: newUpdates };
    }),

  // Task updates
  taskUpdates: new Map(),
  updateTask: (taskId, update) =>
    set((state) => {
      const newUpdates = new Map(state.taskUpdates);
      newUpdates.set(taskId, { ...newUpdates.get(taskId), ...update });
      return { taskUpdates: newUpdates };
    }),
  clearTaskUpdate: (taskId) =>
    set((state) => {
      const newUpdates = new Map(state.taskUpdates);
      newUpdates.delete(taskId);
      return { taskUpdates: newUpdates };
    }),

  // Notifications
  notifications: [],
  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        {
          ...notification,
          id: crypto.randomUUID(),
          timestamp: new Date().toISOString(),
          read: false,
        },
        ...state.notifications,
      ].slice(0, 50), // Keep last 50 notifications
    })),
  markNotificationRead: (id) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
    })),
  clearNotifications: () => set({ notifications: [] }),
}));
