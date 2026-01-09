import { useState, useEffect, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useMetrics } from '@/features/system/hooks/useSystem';

interface DataPoint {
  time: string;
  cpu: number;
  memory: number;
  throughput: number;
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; stroke: string }>; label?: string }) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-border bg-popover p-3 shadow-lg">
        <p className="mb-2 text-sm font-medium">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="flex items-center gap-2 text-xs">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: entry.stroke }}
            />
            <span className="capitalize">{entry.name}:</span>
            <span className="font-semibold">
              {entry.name === 'throughput'
                ? `${entry.value.toFixed(2)}/s`
                : `${entry.value.toFixed(1)}%`}
            </span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export function PerformanceChart() {
  const { data: metrics } = useMetrics();
  const [dataHistory, setDataHistory] = useState<DataPoint[]>([]);
  const [selectedMetric, setSelectedMetric] = useState<'all' | 'cpu' | 'memory' | 'throughput'>('all');

  // Update history when metrics change
  useEffect(() => {
    if (metrics) {
      const now = new Date();
      const newPoint: DataPoint = {
        time: now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        cpu: metrics.cpu_usage,
        memory: metrics.memory_usage,
        throughput: metrics.tasks_per_second,
      };

      setDataHistory((prev) => {
        const updated = [...prev, newPoint];
        // Keep last 30 data points (about 2.5 minutes at 5s intervals)
        return updated.slice(-30);
      });
    }
  }, [metrics]);

  const chartLines = useMemo(() => {
    switch (selectedMetric) {
      case 'cpu':
        return [{ dataKey: 'cpu', stroke: '#8b5cf6', name: 'CPU' }];
      case 'memory':
        return [{ dataKey: 'memory', stroke: '#06b6d4', name: 'Memory' }];
      case 'throughput':
        return [{ dataKey: 'throughput', stroke: '#22c55e', name: 'Throughput' }];
      default:
        return [
          { dataKey: 'cpu', stroke: '#8b5cf6', name: 'CPU' },
          { dataKey: 'memory', stroke: '#06b6d4', name: 'Memory' },
          { dataKey: 'throughput', stroke: '#22c55e', name: 'Throughput' },
        ];
    }
  }, [selectedMetric]);

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <TrendingUp className="h-5 w-5 text-primary" />
            Performance Metrics
          </CardTitle>
          <Tabs value={selectedMetric} onValueChange={(v) => setSelectedMetric(v as typeof selectedMetric)}>
            <TabsList className="h-8">
              <TabsTrigger value="all" className="text-xs px-2">All</TabsTrigger>
              <TabsTrigger value="cpu" className="text-xs px-2">CPU</TabsTrigger>
              <TabsTrigger value="memory" className="text-xs px-2">Memory</TabsTrigger>
              <TabsTrigger value="throughput" className="text-xs px-2">Tasks</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          {dataHistory.length < 2 ? (
            <div className="flex h-full flex-col items-center justify-center text-muted-foreground">
              <TrendingUp className="mb-2 h-8 w-8 animate-pulse" />
              <p>Collecting performance data...</p>
              <p className="text-xs mt-1">Chart will appear shortly</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dataHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#9ca3af', fontSize: 10 }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fill: '#9ca3af', fontSize: 10 }}
                  domain={selectedMetric === 'throughput' ? ['auto', 'auto'] : [0, 100]}
                  tickFormatter={(value) =>
                    selectedMetric === 'throughput' ? value.toFixed(1) : `${value}%`
                  }
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  formatter={(value) => (
                    <span className="text-xs text-muted-foreground">{value}</span>
                  )}
                />
                {chartLines.map((line) => (
                  <Line
                    key={line.dataKey}
                    type="monotone"
                    dataKey={line.dataKey}
                    stroke={line.stroke}
                    name={line.name}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                    animationDuration={300}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
