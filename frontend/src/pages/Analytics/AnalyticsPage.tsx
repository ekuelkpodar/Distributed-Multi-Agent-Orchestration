import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Zap,
  BarChart3,
  LineChart,
  Brain,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// Types
interface TrendData {
  current: number;
  previous: number;
  change_percent: number;
  direction: 'up' | 'down' | 'stable';
}

interface SystemMetrics {
  timestamp: string;
  active_agents: number;
  idle_agents: number;
  failed_agents: number;
  pending_tasks: number;
  running_tasks: number;
  completed_tasks_24h: number;
  failed_tasks_24h: number;
  avg_queue_wait_time_ms: number;
  avg_execution_time_ms: number;
}

interface PerformanceAnalysis {
  score: number;
  grade: string;
  strengths: string[];
  weaknesses: string[];
  bottlenecks: string[];
  recommendations: string[];
}

interface Anomaly {
  metric_name: string;
  detected_at: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  expected_value: number;
  actual_value: number;
  deviation_percent: number;
  possible_causes: string[];
  suggested_actions: string[];
}

interface Insight {
  id: string;
  type: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  impact: string;
  recommendations: string[];
  confidence: number;
  created_at: string;
}

// Mock data for demonstration
const mockSystemMetrics: SystemMetrics = {
  timestamp: new Date().toISOString(),
  active_agents: 12,
  idle_agents: 3,
  failed_agents: 1,
  pending_tasks: 45,
  running_tasks: 8,
  completed_tasks_24h: 1247,
  failed_tasks_24h: 23,
  avg_queue_wait_time_ms: 1250,
  avg_execution_time_ms: 3420,
};

const mockTrending: Record<string, TrendData> = {
  completed_tasks: { current: 1247, previous: 1180, change_percent: 5.68, direction: 'up' },
  failed_tasks: { current: 23, previous: 31, change_percent: -25.81, direction: 'down' },
  total_tasks: { current: 1270, previous: 1211, change_percent: 4.87, direction: 'up' },
};

const mockPerformance: PerformanceAnalysis = {
  score: 87,
  grade: 'B+',
  strengths: [
    'High task success rate (98.2%)',
    'Efficient agent utilization',
    'Fast average execution time',
  ],
  weaknesses: [
    'Queue wait time slightly elevated',
    'One agent currently in failed state',
  ],
  bottlenecks: [
    'Research agent pool approaching capacity',
  ],
  recommendations: [
    'Consider scaling up research agent pool',
    'Investigate failed agent for root cause',
    'Optimize queue scheduling for peak hours',
    'Enable auto-scaling based on queue depth',
  ],
};

const mockAnomalies: Anomaly[] = [
  {
    metric_name: 'task_failure_rate',
    detected_at: new Date().toISOString(),
    severity: 'medium',
    expected_value: 1.5,
    actual_value: 2.8,
    deviation_percent: 86.67,
    possible_causes: ['Resource constraints', 'External service issues'],
    suggested_actions: ['Check agent resources', 'Review error logs'],
  },
];

const mockInsights: Insight[] = [
  {
    id: '1',
    type: 'optimization',
    priority: 'medium',
    title: 'Task Queue Optimization',
    description: 'Analysis shows that task distribution could be improved for better throughput.',
    impact: 'Potential 15% improvement in overall task completion time.',
    recommendations: [
      'Enable priority-based scheduling',
      'Implement task batching for similar operations',
    ],
    confidence: 0.85,
    created_at: new Date().toISOString(),
  },
  {
    id: '2',
    type: 'prediction',
    priority: 'low',
    title: 'Expected Load Increase',
    description: 'Based on historical patterns, expect 20% higher load in the next 2 hours.',
    impact: 'May need additional agent capacity to maintain SLA.',
    recommendations: [
      'Pre-scale agent pool',
      'Defer non-critical tasks if needed',
    ],
    confidence: 0.72,
    created_at: new Date().toISOString(),
  },
];

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState('24h');

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  const getGradeColor = (grade: string) => {
    if (grade.startsWith('A')) return 'text-emerald-500';
    if (grade.startsWith('B')) return 'text-blue-500';
    if (grade.startsWith('C')) return 'text-yellow-500';
    if (grade.startsWith('D')) return 'text-orange-500';
    return 'text-red-500';
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'high': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      default: return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    }
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
          <p className="text-muted-foreground">
            Advanced metrics, insights, and AI-powered recommendations
          </p>
        </div>
        <Select value={timeRange} onValueChange={setTimeRange}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1h">Last 1 hour</SelectItem>
            <SelectItem value="6h">Last 6 hours</SelectItem>
            <SelectItem value="24h">Last 24 hours</SelectItem>
            <SelectItem value="7d">Last 7 days</SelectItem>
            <SelectItem value="30d">Last 30 days</SelectItem>
          </SelectContent>
        </Select>
      </motion.div>

      {/* Performance Score Card */}
      <motion.div variants={itemVariants}>
        <Card className="bg-gradient-to-br from-card to-card/50 border-primary/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className="relative">
                  <div className="w-24 h-24 rounded-full border-4 border-primary/20 flex items-center justify-center">
                    <span className={`text-3xl font-bold ${getGradeColor(mockPerformance.grade)}`}>
                      {mockPerformance.grade}
                    </span>
                  </div>
                  <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 bg-background px-2 py-0.5 rounded-full border text-xs">
                    {mockPerformance.score}/100
                  </div>
                </div>
                <div>
                  <h2 className="text-xl font-semibold">System Performance Score</h2>
                  <p className="text-muted-foreground">Based on task success, throughput, and resource utilization</p>
                </div>
              </div>
              <Button variant="outline" className="gap-2">
                <Brain className="h-4 w-4" />
                Get AI Analysis
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Metrics Overview */}
      <motion.div variants={itemVariants} className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Completed Tasks (24h)</p>
                <p className="text-2xl font-bold">{mockSystemMetrics.completed_tasks_24h.toLocaleString()}</p>
              </div>
              <div className={`flex items-center gap-1 text-sm ${mockTrending.completed_tasks.direction === 'up' ? 'text-emerald-500' : 'text-red-500'}`}>
                {mockTrending.completed_tasks.direction === 'up' ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                {Math.abs(mockTrending.completed_tasks.change_percent).toFixed(1)}%
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Failed Tasks (24h)</p>
                <p className="text-2xl font-bold">{mockSystemMetrics.failed_tasks_24h}</p>
              </div>
              <div className={`flex items-center gap-1 text-sm ${mockTrending.failed_tasks.direction === 'down' ? 'text-emerald-500' : 'text-red-500'}`}>
                {mockTrending.failed_tasks.direction === 'down' ? <TrendingDown className="h-4 w-4" /> : <TrendingUp className="h-4 w-4" />}
                {Math.abs(mockTrending.failed_tasks.change_percent).toFixed(1)}%
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Execution Time</p>
                <p className="text-2xl font-bold">{(mockSystemMetrics.avg_execution_time_ms / 1000).toFixed(1)}s</p>
              </div>
              <Clock className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Queue Wait</p>
                <p className="text-2xl font-bold">{(mockSystemMetrics.avg_queue_wait_time_ms / 1000).toFixed(1)}s</p>
              </div>
              <Activity className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Tabs for detailed views */}
      <motion.div variants={itemVariants}>
        <Tabs defaultValue="insights" className="space-y-4">
          <TabsList>
            <TabsTrigger value="insights" className="gap-2">
              <Brain className="h-4 w-4" />
              AI Insights
            </TabsTrigger>
            <TabsTrigger value="anomalies" className="gap-2">
              <AlertTriangle className="h-4 w-4" />
              Anomalies
            </TabsTrigger>
            <TabsTrigger value="performance" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              Performance
            </TabsTrigger>
          </TabsList>

          <TabsContent value="insights" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {mockInsights.map((insight) => (
                <Card key={insight.id} className="hover:border-primary/50 transition-colors">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={getPriorityColor(insight.priority)}>
                          {insight.priority}
                        </Badge>
                        <Badge variant="secondary">{insight.type}</Badge>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {Math.round(insight.confidence * 100)}% confidence
                      </span>
                    </div>
                    <CardTitle className="text-lg mt-2">{insight.title}</CardTitle>
                    <CardDescription>{insight.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-start gap-2 text-sm">
                        <Zap className="h-4 w-4 text-yellow-500 mt-0.5" />
                        <span className="text-muted-foreground">{insight.impact}</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium mb-1">Recommendations:</p>
                        <ul className="text-sm text-muted-foreground space-y-1">
                          {insight.recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <CheckCircle className="h-3 w-3 text-emerald-500 mt-1" />
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="anomalies" className="space-y-4">
            {mockAnomalies.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <CheckCircle className="h-12 w-12 text-emerald-500 mb-4" />
                  <h3 className="text-lg font-semibold">No Anomalies Detected</h3>
                  <p className="text-muted-foreground">System is operating within normal parameters</p>
                </CardContent>
              </Card>
            ) : (
              mockAnomalies.map((anomaly, i) => (
                <Card key={i} className="border-yellow-500/20">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-yellow-500" />
                        <CardTitle>{anomaly.metric_name.replace(/_/g, ' ').toUpperCase()}</CardTitle>
                      </div>
                      <Badge variant="outline" className={getPriorityColor(anomaly.severity)}>
                        {anomaly.severity}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <p className="text-sm text-muted-foreground">Expected</p>
                        <p className="text-lg font-semibold">{anomaly.expected_value.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Actual</p>
                        <p className="text-lg font-semibold text-yellow-500">{anomaly.actual_value.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Deviation</p>
                        <p className="text-lg font-semibold text-red-500">+{anomaly.deviation_percent.toFixed(1)}%</p>
                      </div>
                    </div>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium mb-2">Possible Causes:</p>
                        <ul className="text-sm text-muted-foreground space-y-1">
                          {anomaly.possible_causes.map((cause, j) => (
                            <li key={j}>• {cause}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="text-sm font-medium mb-2">Suggested Actions:</p>
                        <ul className="text-sm text-muted-foreground space-y-1">
                          {anomaly.suggested_actions.map((action, j) => (
                            <li key={j}>• {action}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </TabsContent>

          <TabsContent value="performance" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle className="h-5 w-5 text-emerald-500" />
                    Strengths
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {mockPerformance.strengths.map((strength, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-2" />
                        {strength}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <XCircle className="h-5 w-5 text-red-500" />
                    Areas for Improvement
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {mockPerformance.weaknesses.map((weakness, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <div className="h-1.5 w-1.5 rounded-full bg-red-500 mt-2" />
                        {weakness}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-yellow-500" />
                  Recommendations
                </CardTitle>
                <CardDescription>AI-powered suggestions to improve system performance</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2">
                  {mockPerformance.recommendations.map((rec, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
                        {i + 1}
                      </span>
                      <p className="text-sm">{rec}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </motion.div>
    </motion.div>
  );
}
