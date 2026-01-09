import { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { ListTodo } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useTasks } from '@/features/tasks/hooks/useTasks';

const STATUS_COLORS: Record<string, string> = {
  pending: '#f59e0b',
  queued: '#8b5cf6',
  running: '#3b82f6',
  completed: '#22c55e',
  failed: '#ef4444',
  cancelled: '#6b7280',
};

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; fill: string }>; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-border bg-popover p-3 shadow-lg">
        <p className="mb-2 text-sm font-medium">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="flex items-center gap-2 text-xs">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: entry.fill }}
            />
            <span className="capitalize">{entry.name}:</span>
            <span className="font-semibold">{entry.value}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export function TasksOverview() {
  const { data, isLoading } = useTasks({ page_size: 100 });

  const chartData = useMemo(() => {
    if (!data?.tasks) return [];

    // Group tasks by status
    const statusCounts: Record<string, number> = {
      pending: 0,
      queued: 0,
      running: 0,
      completed: 0,
      failed: 0,
      cancelled: 0,
    };

    data.tasks.forEach((task) => {
      if (statusCounts[task.status] !== undefined) {
        statusCounts[task.status]++;
      }
    });

    // Create chart data structure
    return [
      {
        name: 'Tasks',
        pending: statusCounts.pending,
        queued: statusCounts.queued,
        running: statusCounts.running,
        completed: statusCounts.completed,
        failed: statusCounts.failed,
      },
    ];
  }, [data]);

  const statusSummary = useMemo(() => {
    if (!chartData.length) return null;
    const totals = chartData[0];
    return {
      total: Object.values(totals).reduce((sum: number, val) => sum + (typeof val === 'number' ? val : 0), 0) - (typeof totals.name === 'string' ? 0 : 0),
      active: (totals.pending || 0) + (totals.queued || 0) + (totals.running || 0),
      completed: totals.completed || 0,
      failed: totals.failed || 0,
    };
  }, [chartData]);

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <ListTodo className="h-5 w-5 text-primary" />
          Tasks Overview
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex h-[300px] items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : (
          <>
            {/* Status Summary */}
            <div className="mb-4 grid grid-cols-4 gap-2">
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-lg bg-background/50 p-2 text-center"
              >
                <p className="text-xl font-bold">{statusSummary?.total || 0}</p>
                <p className="text-xs text-muted-foreground">Total</p>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="rounded-lg bg-blue-500/10 p-2 text-center"
              >
                <p className="text-xl font-bold text-blue-400">{statusSummary?.active || 0}</p>
                <p className="text-xs text-muted-foreground">Active</p>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="rounded-lg bg-green-500/10 p-2 text-center"
              >
                <p className="text-xl font-bold text-green-400">{statusSummary?.completed || 0}</p>
                <p className="text-xs text-muted-foreground">Completed</p>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="rounded-lg bg-red-500/10 p-2 text-center"
              >
                <p className="text-xl font-bold text-red-400">{statusSummary?.failed || 0}</p>
                <p className="text-xs text-muted-foreground">Failed</p>
              </motion.div>
            </div>

            {/* Bar Chart */}
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fill: '#9ca3af', fontSize: 12 }}
                    width={60}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend
                    formatter={(value) => (
                      <span className="text-xs capitalize text-muted-foreground">
                        {value}
                      </span>
                    )}
                  />
                  <Bar dataKey="pending" fill={STATUS_COLORS.pending} stackId="stack" />
                  <Bar dataKey="queued" fill={STATUS_COLORS.queued} stackId="stack" />
                  <Bar dataKey="running" fill={STATUS_COLORS.running} stackId="stack" />
                  <Bar dataKey="completed" fill={STATUS_COLORS.completed} stackId="stack" />
                  <Bar dataKey="failed" fill={STATUS_COLORS.failed} stackId="stack" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
