import { useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useSystemStore } from '@/stores/systemStore';
import type { SystemEvent } from '@/types/api.types';

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8000';

interface WebSocketMessage {
  type: string;
  payload: unknown;
}

export function useWebSocket() {
  const socketRef = useRef<Socket | null>(null);
  const { setConnected, addEvent, updateAgent, updateTask, addNotification } = useSystemStore();

  const handleMessage = useCallback(
    (message: WebSocketMessage) => {
      switch (message.type) {
        case 'agent.spawned':
        case 'agent.started':
        case 'agent.stopped':
        case 'agent.heartbeat': {
          const payload = message.payload as { agent_id: string; status?: string };
          updateAgent(payload.agent_id, payload as never);
          addEvent({
            id: crypto.randomUUID(),
            type: message.type as SystemEvent['type'],
            timestamp: new Date().toISOString(),
            severity: message.type === 'agent.stopped' ? 'warning' : 'info',
            message: `Agent ${message.type.split('.')[1]}`,
            agent_id: payload.agent_id,
          });
          break;
        }

        case 'task.assigned':
        case 'task.started':
        case 'task.progress':
        case 'task.completed':
        case 'task.failed': {
          const payload = message.payload as { task_id: string; status?: string; agent_id?: string };
          updateTask(payload.task_id, payload as never);
          addEvent({
            id: crypto.randomUUID(),
            type: message.type as SystemEvent['type'],
            timestamp: new Date().toISOString(),
            severity: message.type === 'task.failed' ? 'error' : message.type === 'task.completed' ? 'success' : 'info',
            message: `Task ${message.type.split('.')[1]}`,
            task_id: payload.task_id,
            agent_id: payload.agent_id,
          });

          // Add notification for task completion/failure
          if (message.type === 'task.completed') {
            addNotification({
              type: 'success',
              title: 'Task Completed',
              message: `Task ${payload.task_id.slice(0, 8)} completed successfully`,
            });
          } else if (message.type === 'task.failed') {
            addNotification({
              type: 'error',
              title: 'Task Failed',
              message: `Task ${payload.task_id.slice(0, 8)} failed`,
            });
          }
          break;
        }

        case 'system.alert': {
          const payload = message.payload as { severity: string; message: string };
          addNotification({
            type: payload.severity as 'info' | 'warning' | 'error',
            title: 'System Alert',
            message: payload.message,
          });
          break;
        }

        default:
          console.log('Unknown WebSocket message type:', message.type);
      }
    },
    [addEvent, updateAgent, updateTask, addNotification]
  );

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return;

    socketRef.current = io(WS_URL, {
      path: '/ws/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });

    socketRef.current.on('connect', () => {
      console.log('WebSocket connected');
      setConnected(true);
    });

    socketRef.current.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      setConnected(false);
    });

    socketRef.current.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setConnected(false);
    });

    socketRef.current.on('message', handleMessage);
    socketRef.current.on('event', handleMessage);
  }, [setConnected, handleMessage]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setConnected(false);
    }
  }, [setConnected]);

  const sendMessage = useCallback((type: string, payload: unknown) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(type, payload);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected: socketRef.current?.connected ?? false,
    connect,
    disconnect,
    sendMessage,
  };
}
