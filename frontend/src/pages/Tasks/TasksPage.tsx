import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ListTodo, Grid3X3, List } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/EmptyState';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { useTasks, useCancelTask, useRetryTask, useDeleteTask } from '@/features/tasks/hooks/useTasks';
import { TaskCard } from './components/TaskCard';
import { TaskFilters } from './components/TaskFilters';
import { SubmitTaskModal } from './components/SubmitTaskModal';
import type { TaskStatus, TaskPriority } from '@/types/api.types';

type ViewMode = 'grid' | 'list';

export default function TasksPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | 'all'>('all');

  const { data, isLoading, error } = useTasks();
  const cancelTask = useCancelTask();
  const retryTask = useRetryTask();
  const deleteTask = useDeleteTask();

  // Filter tasks
  const filteredTasks = useMemo(() => {
    if (!data?.tasks) return [];

    return data.tasks.filter((task) => {
      // Search filter
      if (search) {
        const searchLower = search.toLowerCase();
        const matchesSearch =
          task.description.toLowerCase().includes(searchLower) ||
          task.id.toLowerCase().includes(searchLower);
        if (!matchesSearch) return false;
      }

      // Status filter
      if (statusFilter !== 'all' && task.status !== statusFilter) {
        return false;
      }

      // Priority filter
      if (priorityFilter !== 'all' && task.priority !== priorityFilter) {
        return false;
      }

      return true;
    });
  }, [data?.tasks, search, statusFilter, priorityFilter]);

  const handleClearFilters = () => {
    setSearch('');
    setStatusFilter('all');
    setPriorityFilter('all');
  };

  const handleCancel = async (taskId: string) => {
    if (confirm('Are you sure you want to cancel this task?')) {
      try {
        await cancelTask.mutateAsync(taskId);
      } catch (error) {
        console.error('Failed to cancel task:', error);
      }
    }
  };

  const handleRetry = async (taskId: string) => {
    try {
      await retryTask.mutateAsync(taskId);
    } catch (error) {
      console.error('Failed to retry task:', error);
    }
  };

  const handleDelete = async (taskId: string) => {
    if (confirm('Are you sure you want to delete this task?')) {
      try {
        await deleteTask.mutateAsync(taskId);
      } catch (error) {
        console.error('Failed to delete task:', error);
      }
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05,
      },
    },
  };

  // Task stats
  const stats = useMemo(() => {
    if (!data?.tasks) return null;
    return {
      total: data.total,
      pending: data.tasks.filter((t) => t.status === 'pending').length,
      running: data.tasks.filter((t) => t.status === 'running').length,
      completed: data.tasks.filter((t) => t.status === 'completed').length,
      failed: data.tasks.filter((t) => t.status === 'failed').length,
    };
  }, [data]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tasks</h1>
          <p className="text-muted-foreground">
            Manage and monitor task execution
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* View Toggle */}
          <div className="flex items-center rounded-lg border border-border bg-background p-1">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon"
              className="h-8 w-8"
              onClick={() => setViewMode('grid')}
            >
              <Grid3X3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              className="h-8 w-8"
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
          <SubmitTaskModal />
        </div>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-5 gap-3">
          <div className="rounded-lg border border-border/50 bg-card/50 p-3 text-center">
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-xs text-muted-foreground">Total</p>
          </div>
          <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 text-center">
            <p className="text-2xl font-bold text-yellow-400">{stats.pending}</p>
            <p className="text-xs text-muted-foreground">Pending</p>
          </div>
          <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-3 text-center">
            <p className="text-2xl font-bold text-blue-400">{stats.running}</p>
            <p className="text-xs text-muted-foreground">Running</p>
          </div>
          <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-3 text-center">
            <p className="text-2xl font-bold text-green-400">{stats.completed}</p>
            <p className="text-xs text-muted-foreground">Completed</p>
          </div>
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-center">
            <p className="text-2xl font-bold text-red-400">{stats.failed}</p>
            <p className="text-xs text-muted-foreground">Failed</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <TaskFilters
        search={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        priorityFilter={priorityFilter}
        onPriorityFilterChange={setPriorityFilter}
        onClearFilters={handleClearFilters}
      />

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <EmptyState
          icon={ListTodo}
          title="Failed to load tasks"
          description="There was an error loading the tasks. Please try again."
          action={
            <Button onClick={() => window.location.reload()}>
              Retry
            </Button>
          }
        />
      ) : filteredTasks.length === 0 ? (
        <EmptyState
          icon={ListTodo}
          title={data?.tasks?.length === 0 ? 'No tasks yet' : 'No tasks found'}
          description={
            data?.tasks?.length === 0
              ? 'Submit your first task to get started with AI-powered processing.'
              : 'Try adjusting your filters to find tasks.'
          }
          action={
            data?.tasks?.length === 0 ? (
              <SubmitTaskModal />
            ) : (
              <Button variant="outline" onClick={handleClearFilters}>
                Clear Filters
              </Button>
            )
          }
        />
      ) : (
        <>
          {/* Results Count */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>
              Showing <strong className="text-foreground">{filteredTasks.length}</strong> of{' '}
              <strong className="text-foreground">{data?.total ?? 0}</strong> tasks
            </span>
          </div>

          {/* Task Grid/List */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className={
              viewMode === 'grid'
                ? 'grid gap-4 sm:grid-cols-2 lg:grid-cols-3'
                : 'space-y-4'
            }
          >
            <AnimatePresence mode="popLayout">
              {filteredTasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onCancel={handleCancel}
                  onRetry={handleRetry}
                  onDelete={handleDelete}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        </>
      )}
    </div>
  );
}
