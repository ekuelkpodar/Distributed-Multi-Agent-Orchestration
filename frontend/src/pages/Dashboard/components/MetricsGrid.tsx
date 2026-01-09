import { motion } from 'framer-motion';
import {
  Bot,
  CheckCircle2,
  Clock,
  Cpu,
  Gauge,
  ListTodo,
  MemoryStick,
  Zap,
} from 'lucide-react';
import { MetricCard } from '@/components/common/MetricCard';
import { useMetrics } from '@/features/system/hooks/useSystem';

export function MetricsGrid() {
  const { data: metrics, isLoading } = useMetrics();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
    },
  };

  const metricCards = [
    {
      title: 'Active Agents',
      value: metrics?.active_agents ?? 0,
      icon: Bot,
      description: `${metrics?.total_agents ?? 0} total agents`,
      trend: metrics?.active_agents && metrics?.total_agents
        ? Math.round((metrics.active_agents / metrics.total_agents) * 100)
        : 0,
      trendLabel: 'utilization',
      color: 'primary' as const,
    },
    {
      title: 'Running Tasks',
      value: metrics?.running_tasks ?? 0,
      icon: ListTodo,
      description: `${metrics?.pending_tasks ?? 0} pending`,
      trend: metrics?.running_tasks ?? 0,
      trendLabel: 'in progress',
      color: 'secondary' as const,
    },
    {
      title: 'Completed Tasks',
      value: metrics?.completed_tasks ?? 0,
      icon: CheckCircle2,
      description: `${metrics?.failed_tasks ?? 0} failed`,
      trend: metrics?.completed_tasks && (metrics?.completed_tasks + (metrics?.failed_tasks ?? 0)) > 0
        ? Math.round((metrics.completed_tasks / (metrics.completed_tasks + (metrics?.failed_tasks ?? 0))) * 100)
        : 100,
      trendLabel: 'success rate',
      color: 'success' as const,
    },
    {
      title: 'Throughput',
      value: metrics?.tasks_per_second?.toFixed(2) ?? '0.00',
      icon: Zap,
      description: 'tasks/second',
      unit: '/s',
      color: 'warning' as const,
    },
    {
      title: 'Avg Duration',
      value: metrics?.avg_task_duration_ms
        ? metrics.avg_task_duration_ms > 1000
          ? (metrics.avg_task_duration_ms / 1000).toFixed(1)
          : metrics.avg_task_duration_ms.toFixed(0)
        : '0',
      icon: Clock,
      description: metrics?.avg_task_duration_ms && metrics.avg_task_duration_ms > 1000 ? 'seconds' : 'milliseconds',
      unit: metrics?.avg_task_duration_ms && metrics.avg_task_duration_ms > 1000 ? 's' : 'ms',
      color: 'info' as const,
    },
    {
      title: 'CPU Usage',
      value: metrics?.cpu_usage?.toFixed(1) ?? '0.0',
      icon: Cpu,
      description: 'system CPU',
      unit: '%',
      trend: metrics?.cpu_usage ?? 0,
      trendDirection: 'down' as const,
      color: metrics?.cpu_usage && metrics.cpu_usage > 80 ? 'error' as const : 'primary' as const,
    },
    {
      title: 'Memory Usage',
      value: metrics?.memory_usage?.toFixed(1) ?? '0.0',
      icon: MemoryStick,
      description: 'system memory',
      unit: '%',
      trend: metrics?.memory_usage ?? 0,
      trendDirection: 'down' as const,
      color: metrics?.memory_usage && metrics.memory_usage > 80 ? 'error' as const : 'secondary' as const,
    },
    {
      title: 'System Load',
      value: metrics?.cpu_usage && metrics?.memory_usage
        ? ((metrics.cpu_usage + metrics.memory_usage) / 2).toFixed(1)
        : '0.0',
      icon: Gauge,
      description: 'average load',
      unit: '%',
      color: 'success' as const,
    },
  ];

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded-lg bg-card/50"
          />
        ))}
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="grid grid-cols-2 gap-4 md:grid-cols-4"
    >
      {metricCards.map((card) => (
        <motion.div key={card.title} variants={itemVariants}>
          <MetricCard
            title={card.title}
            value={card.value}
            icon={card.icon}
            description={card.description}
            trend={card.trend}
            trendLabel={card.trendLabel}
            unit={card.unit}
          />
        </motion.div>
      ))}
    </motion.div>
  );
}
