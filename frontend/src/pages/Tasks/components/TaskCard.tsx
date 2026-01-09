import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Clock,
  MoreVertical,
  X,
  RefreshCw,
  Eye,
  Bot,
  Trash2,
} from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Progress } from '@/components/ui/progress';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { formatRelativeTime, formatDuration } from '@/lib/utils';
import type { Task } from '@/types/api.types';

interface TaskCardProps {
  task: Task;
  onCancel: (taskId: string) => void;
  onRetry: (taskId: string) => void;
  onDelete: (taskId: string) => void;
}

const PRIORITY_COLORS: Record<number, string> = {
  1: 'bg-red-500/20 text-red-400 border-red-500/30',
  2: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  3: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  4: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  5: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

const PRIORITY_LABELS: Record<number, string> = {
  1: 'Critical',
  2: 'High',
  3: 'Medium',
  4: 'Low',
  5: 'Background',
};

export function TaskCard({ task, onCancel, onRetry, onDelete }: TaskCardProps) {
  const navigate = useNavigate();

  const handleViewDetails = () => {
    navigate(`/tasks/${task.id}`);
  };

  const getDuration = () => {
    if (task.started_at && task.completed_at) {
      const start = new Date(task.started_at).getTime();
      const end = new Date(task.completed_at).getTime();
      return formatDuration(end - start);
    }
    if (task.started_at) {
      const start = new Date(task.started_at).getTime();
      const now = Date.now();
      return formatDuration(now - start);
    }
    return null;
  };

  const duration = getDuration();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
    >
      <Card className="group relative border-border/50 bg-card/50 backdrop-blur transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5">
        {/* Status & Priority Badges */}
        <div className="absolute right-4 top-4 flex items-center gap-2">
          <Badge
            variant="outline"
            className={`text-xs ${PRIORITY_COLORS[task.priority]}`}
          >
            {PRIORITY_LABELS[task.priority]}
          </Badge>
          <StatusBadge status={task.status} showPulse size="sm" />
        </div>

        <CardHeader className="pb-3">
          <div className="pr-32">
            <h3 className="font-semibold line-clamp-2">{task.description}</h3>
            <p className="text-xs text-muted-foreground mt-1 font-mono">
              {task.id.slice(0, 8)}...
            </p>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Progress Bar for Running Tasks */}
          {task.status === 'running' && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Progress</span>
                <span>Processing...</span>
              </div>
              <Progress value={undefined} className="h-1.5" />
            </div>
          )}

          {/* Task Info */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            {task.agent_id && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Bot className="h-4 w-4" />
                <span className="truncate font-mono text-xs">
                  {task.agent_id.slice(0, 8)}
                </span>
              </div>
            )}
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>{formatRelativeTime(task.created_at)}</span>
            </div>
          </div>

          {/* Duration */}
          {duration && (
            <div className="text-xs text-muted-foreground">
              Duration: <span className="font-medium">{duration}</span>
            </div>
          )}

          {/* Input/Output Preview */}
          {Object.keys(task.input_data || {}).length > 0 && (
            <div className="rounded-lg bg-background/50 p-2 text-xs">
              <p className="text-muted-foreground mb-1">Input:</p>
              <p className="font-mono truncate">
                {JSON.stringify(task.input_data).slice(0, 100)}...
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-border/50">
            <Button variant="outline" size="sm" onClick={handleViewDetails}>
              <Eye className="mr-1 h-3 w-3" />
              Details
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleViewDetails}>
                  <Eye className="mr-2 h-4 w-4" />
                  View Details
                </DropdownMenuItem>
                {(task.status === 'pending' || task.status === 'running') && (
                  <DropdownMenuItem onClick={() => onCancel(task.id)}>
                    <X className="mr-2 h-4 w-4" />
                    Cancel
                  </DropdownMenuItem>
                )}
                {task.status === 'failed' && (
                  <DropdownMenuItem onClick={() => onRetry(task.id)}>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Retry
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => onDelete(task.id)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
