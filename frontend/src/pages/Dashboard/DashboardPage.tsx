import { motion } from 'framer-motion';
import { useWebSocket } from '@/hooks/useWebSocket';
import { SystemOverview } from './components/SystemOverview';
import { MetricsGrid } from './components/MetricsGrid';
import { ActivityFeed } from './components/ActivityFeed';
import { AgentStatusChart } from './components/AgentStatusChart';
import { TasksOverview } from './components/TasksOverview';
import { PerformanceChart } from './components/PerformanceChart';
import { QuickActions } from './components/QuickActions';

export default function DashboardPage() {
  // Initialize WebSocket connection
  useWebSocket();

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
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Page Header */}
      <motion.div variants={itemVariants}>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Real-time overview of your multi-agent orchestration system
        </p>
      </motion.div>

      {/* Metrics Grid */}
      <motion.div variants={itemVariants}>
        <MetricsGrid />
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column - Charts */}
        <motion.div variants={itemVariants} className="lg:col-span-2 space-y-6">
          <PerformanceChart />
          <div className="grid gap-6 md:grid-cols-2">
            <AgentStatusChart />
            <TasksOverview />
          </div>
        </motion.div>

        {/* Right Column - Activity & Actions */}
        <motion.div variants={itemVariants} className="space-y-6">
          <SystemOverview />
          <QuickActions />
          <ActivityFeed />
        </motion.div>
      </div>
    </motion.div>
  );
}
