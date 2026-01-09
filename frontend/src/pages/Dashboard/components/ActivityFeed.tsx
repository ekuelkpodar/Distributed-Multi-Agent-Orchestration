import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  Bot,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
  XCircle,
  Clock,
  Zap,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useSystemStore } from '@/stores/systemStore';
import { formatRelativeTime } from '@/lib/utils';
import { cn } from '@/lib/utils';
import type { SystemEvent } from '@/types/api.types';

const getEventIcon = (type: string) => {
  switch (type) {
    case 'agent.spawned':
      return <Bot className="h-4 w-4 text-purple-400" />;
    case 'agent.started':
      return <PlayCircle className="h-4 w-4 text-green-400" />;
    case 'agent.stopped':
      return <XCircle className="h-4 w-4 text-yellow-400" />;
    case 'agent.heartbeat':
      return <Activity className="h-4 w-4 text-blue-400" />;
    case 'task.assigned':
      return <Zap className="h-4 w-4 text-cyan-400" />;
    case 'task.started':
      return <PlayCircle className="h-4 w-4 text-blue-400" />;
    case 'task.progress':
      return <Clock className="h-4 w-4 text-yellow-400" />;
    case 'task.completed':
      return <CheckCircle2 className="h-4 w-4 text-green-400" />;
    case 'task.failed':
      return <AlertCircle className="h-4 w-4 text-red-400" />;
    case 'system.alert':
      return <AlertCircle className="h-4 w-4 text-orange-400" />;
    default:
      return <Activity className="h-4 w-4 text-muted-foreground" />;
  }
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'success':
      return 'bg-green-500/10 border-green-500/30 text-green-400';
    case 'warning':
      return 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400';
    case 'error':
      return 'bg-red-500/10 border-red-500/30 text-red-400';
    default:
      return 'bg-blue-500/10 border-blue-500/30 text-blue-400';
  }
};

function EventItem({ event }: { event: SystemEvent }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className={cn(
        'flex items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-background/50',
        getSeverityColor(event.severity)
      )}
    >
      <div className="mt-0.5">{getEventIcon(event.type)}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium truncate">{event.message}</p>
          <Badge variant="outline" className="text-xs shrink-0">
            {event.type.split('.')[0]}
          </Badge>
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          <span>{formatRelativeTime(event.timestamp)}</span>
          {event.agent_id && (
            <>
              <span>•</span>
              <span className="font-mono truncate">Agent: {event.agent_id.slice(0, 8)}</span>
            </>
          )}
          {event.task_id && (
            <>
              <span>•</span>
              <span className="font-mono truncate">Task: {event.task_id.slice(0, 8)}</span>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export function ActivityFeed() {
  const events = useSystemStore((state) => state.events);

  // Generate some demo events if none exist
  const displayEvents: SystemEvent[] = events.length > 0 ? events : [
    {
      id: '1',
      type: 'agent.started',
      timestamp: new Date(Date.now() - 60000).toISOString(),
      severity: 'success',
      message: 'Research Agent initialized',
      agent_id: 'agent-001',
    },
    {
      id: '2',
      type: 'task.assigned',
      timestamp: new Date(Date.now() - 120000).toISOString(),
      severity: 'info',
      message: 'New task assigned to Research Agent',
      task_id: 'task-001',
      agent_id: 'agent-001',
    },
    {
      id: '3',
      type: 'task.completed',
      timestamp: new Date(Date.now() - 180000).toISOString(),
      severity: 'success',
      message: 'Task completed successfully',
      task_id: 'task-001',
      agent_id: 'agent-001',
    },
    {
      id: '4',
      type: 'agent.heartbeat',
      timestamp: new Date(Date.now() - 240000).toISOString(),
      severity: 'info',
      message: 'Agent heartbeat received',
      agent_id: 'agent-002',
    },
  ];

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Activity className="h-5 w-5 text-primary" />
          Activity Feed
          {events.length > 0 && (
            <Badge variant="secondary" className="ml-2">
              {events.length}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px] pr-4">
          <AnimatePresence mode="popLayout">
            <div className="space-y-2">
              {displayEvents.slice(0, 20).map((event) => (
                <EventItem key={event.id} event={event} />
              ))}
            </div>
          </AnimatePresence>
          {displayEvents.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Activity className="mb-2 h-8 w-8" />
              <p>No recent activity</p>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
