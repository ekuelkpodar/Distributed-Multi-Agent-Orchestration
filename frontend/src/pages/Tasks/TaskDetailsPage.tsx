import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  ListTodo,
  Clock,
  Bot,
  Play,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Trash2,
  Copy,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/common/StatusBadge';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { EmptyState } from '@/components/common/EmptyState';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useTask, useCancelTask, useRetryTask, useDeleteTask } from '@/features/tasks/hooks/useTasks';
import { formatRelativeTime, formatDuration } from '@/lib/utils';

const PRIORITY_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: 'Critical', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
  2: { label: 'High', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  3: { label: 'Medium', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  4: { label: 'Low', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  5: { label: 'Background', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
};

export default function TaskDetailsPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const { data: task, isLoading, error } = useTask(taskId || '');
  const cancelTask = useCancelTask();
  const retryTask = useRetryTask();
  const deleteTask = useDeleteTask();

  const handleCancel = async () => {
    if (!taskId) return;
    if (confirm('Are you sure you want to cancel this task?')) {
      try {
        await cancelTask.mutateAsync(taskId);
      } catch (error) {
        console.error('Failed to cancel task:', error);
      }
    }
  };

  const handleRetry = async () => {
    if (!taskId) return;
    try {
      await retryTask.mutateAsync(taskId);
    } catch (error) {
      console.error('Failed to retry task:', error);
    }
  };

  const handleDelete = async () => {
    if (!taskId) return;
    if (confirm('Are you sure you want to delete this task?')) {
      try {
        await deleteTask.mutateAsync(taskId);
        navigate('/tasks');
      } catch (error) {
        console.error('Failed to delete task:', error);
      }
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !task) {
    return (
      <EmptyState
        icon={ListTodo}
        title="Task not found"
        description="The task you're looking for doesn't exist or has been deleted."
        action={
          <Button onClick={() => navigate('/tasks')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Tasks
          </Button>
        }
      />
    );
  }

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
  const priorityInfo = PRIORITY_LABELS[task.priority];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/tasks')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <ListTodo className="h-5 w-5 text-primary" />
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className={priorityInfo.color}>
                  {priorityInfo.label}
                </Badge>
                <StatusBadge status={task.status} showPulse />
              </div>
            </div>
            <h1 className="text-xl font-bold">{task.description}</h1>
            <p className="text-sm text-muted-foreground font-mono mt-1">
              ID: {task.id}
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 ml-1"
                onClick={() => copyToClipboard(task.id)}
              >
                <Copy className="h-3 w-3" />
              </Button>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {(task.status === 'pending' || task.status === 'running') && (
            <Button variant="outline" onClick={handleCancel}>
              <XCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
          {task.status === 'failed' && (
            <Button variant="outline" onClick={handleRetry}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry
            </Button>
          )}
          <Button variant="destructive" onClick={handleDelete}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Progress Bar for Running Tasks */}
      {task.status === 'running' && (
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardContent className="py-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Task in Progress</span>
              <span className="text-sm text-muted-foreground">Processing...</span>
            </div>
            <Progress value={undefined} className="h-2" />
          </CardContent>
        </Card>
      )}

      {/* Content */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="input">Input Data</TabsTrigger>
          <TabsTrigger value="output">Output Data</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Task Info */}
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg">Task Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Status</p>
                    <StatusBadge status={task.status} className="mt-1" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Priority</p>
                    <Badge variant="outline" className={`mt-1 ${priorityInfo.color}`}>
                      {task.priority} - {priorityInfo.label}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Created</p>
                    <p>{formatRelativeTime(task.created_at)}</p>
                  </div>
                  {duration && (
                    <div>
                      <p className="text-sm text-muted-foreground">Duration</p>
                      <p>{duration}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Agent Info */}
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg">Agent Assignment</CardTitle>
              </CardHeader>
              <CardContent>
                {task.agent_id ? (
                  <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                      <Bot className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Assigned Agent</p>
                      <p className="font-mono">{task.agent_id}</p>
                      <Button
                        variant="link"
                        className="h-auto p-0 text-primary"
                        onClick={() => navigate(`/agents/${task.agent_id}`)}
                      >
                        View Agent Details
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
                    <Bot className="mb-2 h-8 w-8" />
                    <p>Not yet assigned</p>
                    <p className="text-sm">Waiting for available agent</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Status Card */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Status Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center py-6">
                <div className="flex items-center gap-8">
                  {task.status === 'completed' && (
                    <div className="flex flex-col items-center text-green-400">
                      <CheckCircle2 className="h-16 w-16" />
                      <p className="mt-2 font-semibold">Completed Successfully</p>
                    </div>
                  )}
                  {task.status === 'failed' && (
                    <div className="flex flex-col items-center text-red-400">
                      <XCircle className="h-16 w-16" />
                      <p className="mt-2 font-semibold">Task Failed</p>
                    </div>
                  )}
                  {task.status === 'running' && (
                    <div className="flex flex-col items-center text-blue-400">
                      <div className="relative">
                        <Play className="h-16 w-16" />
                        <span className="absolute -right-1 -top-1 flex h-4 w-4">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                          <span className="relative inline-flex rounded-full h-4 w-4 bg-blue-500" />
                        </span>
                      </div>
                      <p className="mt-2 font-semibold">In Progress</p>
                    </div>
                  )}
                  {(task.status === 'pending' || task.status === 'queued') && (
                    <div className="flex flex-col items-center text-yellow-400">
                      <Clock className="h-16 w-16" />
                      <p className="mt-2 font-semibold capitalize">{task.status}</p>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="input">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Input Data</CardTitle>
            </CardHeader>
            <CardContent>
              {Object.keys(task.input_data || {}).length > 0 ? (
                <pre className="rounded-lg bg-background p-4 text-sm font-mono overflow-auto max-h-96">
                  {JSON.stringify(task.input_data, null, 2)}
                </pre>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <p>No input data provided</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="output">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Output Data</CardTitle>
            </CardHeader>
            <CardContent>
              {Object.keys(task.output_data || {}).length > 0 ? (
                <pre className="rounded-lg bg-background p-4 text-sm font-mono overflow-auto max-h-96">
                  {JSON.stringify(task.output_data, null, 2)}
                </pre>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <p>
                    {task.status === 'completed'
                      ? 'No output data generated'
                      : 'Output will appear here when task completes'}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="timeline">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Task Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-start gap-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-500/20">
                    <div className="h-3 w-3 rounded-full bg-green-500" />
                  </div>
                  <div>
                    <p className="font-medium">Task Created</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(task.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                {task.started_at && (
                  <div className="flex items-start gap-4">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500/20">
                      <div className="h-3 w-3 rounded-full bg-blue-500" />
                    </div>
                    <div>
                      <p className="font-medium">Task Started</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(task.started_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                )}

                {task.completed_at && (
                  <div className="flex items-start gap-4">
                    <div className={`flex h-8 w-8 items-center justify-center rounded-full ${
                      task.status === 'completed' ? 'bg-green-500/20' : 'bg-red-500/20'
                    }`}>
                      <div className={`h-3 w-3 rounded-full ${
                        task.status === 'completed' ? 'bg-green-500' : 'bg-red-500'
                      }`} />
                    </div>
                    <div>
                      <p className="font-medium">
                        {task.status === 'completed' ? 'Task Completed' : 'Task Failed'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(task.completed_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
