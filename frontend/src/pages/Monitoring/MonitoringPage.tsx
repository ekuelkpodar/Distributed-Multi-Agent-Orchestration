import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  Cpu,
  MemoryStick,
  HardDrive,
  Wifi,
  WifiOff,
  RefreshCw,
  Download,
} from 'lucide-react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useMetrics, useHealth, useEvents } from '@/features/system/hooks/useSystem';
import { useSystemStore } from '@/stores/systemStore';
import { formatRelativeTime } from '@/lib/utils';

interface MetricHistory {
  time: string;
  cpu: number;
  memory: number;
  activeAgents: number;
  runningTasks: number;
  throughput: number;
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; stroke?: string; fill?: string }>; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-border bg-popover p-3 shadow-lg">
        <p className="mb-2 text-sm font-medium">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="flex items-center gap-2 text-xs">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: entry.stroke || entry.fill }}
            />
            <span className="capitalize">{entry.name}:</span>
            <span className="font-semibold">
              {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
            </span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function MonitoringPage() {
  const { data: metrics } = useMetrics();
  const { data: health } = useHealth();
  const { data: eventsData } = useEvents({ limit: 50 });
  const isConnected = useSystemStore((state) => state.isConnected);
  const realtimeEvents = useSystemStore((state) => state.events);

  const [metricsHistory, setMetricsHistory] = useState<MetricHistory[]>([]);

  // Update metrics history
  useEffect(() => {
    if (metrics) {
      const now = new Date();
      const newPoint: MetricHistory = {
        time: now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        cpu: metrics.cpu_usage,
        memory: metrics.memory_usage,
        activeAgents: metrics.active_agents,
        runningTasks: metrics.running_tasks,
        throughput: metrics.tasks_per_second,
      };

      setMetricsHistory((prev) => {
        const updated = [...prev, newPoint];
        return updated.slice(-60); // Keep last 60 data points (5 minutes at 5s intervals)
      });
    }
  }, [metrics]);

  // Combine API events with real-time events
  const allEvents = useMemo(() => {
    const apiEvents = eventsData?.events || [];
    const combined = [...realtimeEvents, ...apiEvents];
    // Remove duplicates by ID and sort by timestamp
    const unique = Array.from(new Map(combined.map(e => [e.id, e])).values());
    return unique.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [eventsData, realtimeEvents]);

  const getEventColor = (severity: string) => {
    switch (severity) {
      case 'success':
        return 'border-green-500/30 bg-green-500/10';
      case 'warning':
        return 'border-yellow-500/30 bg-yellow-500/10';
      case 'error':
        return 'border-red-500/30 bg-red-500/10';
      default:
        return 'border-blue-500/30 bg-blue-500/10';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Monitoring</h1>
          <p className="text-muted-foreground">
            Real-time system metrics and performance monitoring
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isConnected ? (
            <Badge variant="outline" className="border-green-500/50 text-green-400">
              <Wifi className="mr-1 h-3 w-3" />
              Live
            </Badge>
          ) : (
            <Badge variant="outline" className="border-red-500/50 text-red-400">
              <WifiOff className="mr-1 h-3 w-3" />
              Disconnected
            </Badge>
          )}
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* System Health Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${
                (metrics?.cpu_usage || 0) > 80 ? 'bg-red-500/20' : 'bg-purple-500/20'
              }`}>
                <Cpu className={`h-6 w-6 ${
                  (metrics?.cpu_usage || 0) > 80 ? 'text-red-400' : 'text-purple-400'
                }`} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">CPU Usage</p>
                <p className="text-2xl font-bold">{metrics?.cpu_usage?.toFixed(1) || '0'}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${
                (metrics?.memory_usage || 0) > 80 ? 'bg-red-500/20' : 'bg-cyan-500/20'
              }`}>
                <MemoryStick className={`h-6 w-6 ${
                  (metrics?.memory_usage || 0) > 80 ? 'text-red-400' : 'text-cyan-400'
                }`} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Memory Usage</p>
                <p className="text-2xl font-bold">{metrics?.memory_usage?.toFixed(1) || '0'}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/20">
                <Activity className="h-6 w-6 text-green-400" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Throughput</p>
                <p className="text-2xl font-bold">{metrics?.tasks_per_second?.toFixed(2) || '0'}/s</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50 bg-card/50 backdrop-blur">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${
                health?.status === 'healthy' ? 'bg-green-500/20' :
                health?.status === 'degraded' ? 'bg-yellow-500/20' : 'bg-red-500/20'
              }`}>
                <HardDrive className={`h-6 w-6 ${
                  health?.status === 'healthy' ? 'text-green-400' :
                  health?.status === 'degraded' ? 'text-yellow-400' : 'text-red-400'
                }`} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">System Health</p>
                <p className="text-2xl font-bold capitalize">{health?.status || 'Unknown'}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="metrics" className="space-y-6">
        <TabsList>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="events">Events</TabsTrigger>
          <TabsTrigger value="components">Components</TabsTrigger>
        </TabsList>

        <TabsContent value="metrics" className="space-y-6">
          {/* Resource Usage Chart */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Resource Usage Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                {metricsHistory.length < 2 ? (
                  <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
                    <RefreshCw className="mb-2 h-8 w-8 animate-spin" />
                    <p>Collecting metrics...</p>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={metricsHistory}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="time" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} domain={[0, 100]} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="cpu"
                        name="CPU %"
                        stroke="#8b5cf6"
                        fill="#8b5cf6"
                        fillOpacity={0.2}
                      />
                      <Area
                        type="monotone"
                        dataKey="memory"
                        name="Memory %"
                        stroke="#06b6d4"
                        fill="#06b6d4"
                        fillOpacity={0.2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Agent & Task Activity */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Agent & Task Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[250px]">
                {metricsHistory.length < 2 ? (
                  <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
                    <Activity className="mb-2 h-8 w-8 animate-pulse" />
                    <p>Waiting for activity data...</p>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={metricsHistory}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="time" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="activeAgents"
                        name="Active Agents"
                        stroke="#22c55e"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="runningTasks"
                        name="Running Tasks"
                        stroke="#f59e0b"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="events">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center justify-between text-lg">
                <span>System Events</span>
                <Badge variant="secondary">{allEvents.length} events</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px] pr-4">
                <div className="space-y-3">
                  {allEvents.map((event) => (
                    <div
                      key={event.id}
                      className={`rounded-lg border p-3 ${getEventColor(event.severity)}`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {event.type}
                          </Badge>
                          <Badge
                            variant="outline"
                            className={`text-xs ${
                              event.severity === 'error' ? 'border-red-500/50 text-red-400' :
                              event.severity === 'warning' ? 'border-yellow-500/50 text-yellow-400' :
                              event.severity === 'success' ? 'border-green-500/50 text-green-400' :
                              'border-blue-500/50 text-blue-400'
                            }`}
                          >
                            {event.severity}
                          </Badge>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(event.timestamp)}
                        </span>
                      </div>
                      <p className="mt-2 text-sm">{event.message}</p>
                      {(event.agent_id || event.task_id) && (
                        <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
                          {event.agent_id && (
                            <span>Agent: <code>{event.agent_id.slice(0, 8)}</code></span>
                          )}
                          {event.task_id && (
                            <span>Task: <code>{event.task_id.slice(0, 8)}</code></span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                  {allEvents.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                      <Activity className="mb-2 h-8 w-8" />
                      <p>No events recorded</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="components">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Database Health */}
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg">Database (PostgreSQL)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <Badge
                      variant="outline"
                      className={
                        health?.components?.database?.status === 'healthy'
                          ? 'border-green-500/50 text-green-400'
                          : 'border-red-500/50 text-red-400'
                      }
                    >
                      {health?.components?.database?.status || 'Unknown'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Version</span>
                    <span className="font-mono text-sm">
                      {health?.components?.database?.version || 'N/A'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Redis Health */}
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg">Cache (Redis)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <Badge
                      variant="outline"
                      className={
                        health?.components?.redis?.status === 'healthy'
                          ? 'border-green-500/50 text-green-400'
                          : 'border-red-500/50 text-red-400'
                      }
                    >
                      {health?.components?.redis?.status || 'Unknown'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Version</span>
                    <span className="font-mono text-sm">
                      {health?.components?.redis?.version || 'N/A'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* API Gateway */}
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg">API Gateway</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <Badge variant="outline" className="border-green-500/50 text-green-400">
                      Healthy
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Version</span>
                    <span className="font-mono text-sm">{health?.version || 'N/A'}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* WebSocket */}
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg">WebSocket Connection</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <Badge
                      variant="outline"
                      className={
                        isConnected
                          ? 'border-green-500/50 text-green-400'
                          : 'border-red-500/50 text-red-400'
                      }
                    >
                      {isConnected ? 'Connected' : 'Disconnected'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Events Received</span>
                    <span className="font-mono text-sm">{realtimeEvents.length}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
