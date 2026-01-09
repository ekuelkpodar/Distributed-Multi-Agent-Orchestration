import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Bot } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAgents } from '@/features/agents/hooks/useAgents';

const STATUS_COLORS: Record<string, string> = {
  active: '#22c55e',
  idle: '#3b82f6',
  busy: '#f59e0b',
  offline: '#6b7280',
  failed: '#ef4444',
  starting: '#8b5cf6',
};

const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number; payload: { fill: string } }> }) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-lg border border-border bg-popover p-2 shadow-lg">
        <p className="flex items-center gap-2 text-sm">
          <span
            className="h-3 w-3 rounded-full"
            style={{ backgroundColor: payload[0].payload.fill }}
          />
          <span className="capitalize">{payload[0].name}:</span>
          <span className="font-semibold">{payload[0].value}</span>
        </p>
      </div>
    );
  }
  return null;
};

export function AgentStatusChart() {
  const { data, isLoading } = useAgents();

  const chartData = useMemo(() => {
    if (!data?.agents) return [];

    const statusCounts: Record<string, number> = {};
    data.agents.forEach((agent) => {
      statusCounts[agent.status] = (statusCounts[agent.status] || 0) + 1;
    });

    return Object.entries(statusCounts).map(([status, count]) => ({
      name: status,
      value: count,
      fill: STATUS_COLORS[status] || '#6b7280',
    }));
  }, [data]);

  const totalAgents = data?.total ?? 0;

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Bot className="h-5 w-5 text-primary" />
          Agent Status Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex h-[300px] items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex h-[300px] flex-col items-center justify-center text-muted-foreground">
            <Bot className="mb-2 h-12 w-12" />
            <p>No agents registered</p>
          </div>
        ) : (
          <div className="relative h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  animationBegin={0}
                  animationDuration={1000}
                >
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.fill}
                      stroke="transparent"
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  formatter={(value) => (
                    <span className="text-xs capitalize text-muted-foreground">
                      {value}
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Center label */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 }}
              className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-center"
            >
              <p className="text-3xl font-bold">{totalAgents}</p>
              <p className="text-xs text-muted-foreground">Total Agents</p>
            </motion.div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
