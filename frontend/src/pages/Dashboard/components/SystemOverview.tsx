import { motion } from 'framer-motion';
import { Activity, AlertCircle, CheckCircle2, Server, Wifi, WifiOff } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useHealth } from '@/features/system/hooks/useSystem';
import { useSystemStore } from '@/stores/systemStore';
import { cn } from '@/lib/utils';

export function SystemOverview() {
  const { data: health, isLoading, error } = useHealth();
  const isConnected = useSystemStore((state) => state.isConnected);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-400';
      case 'degraded':
        return 'text-yellow-400';
      case 'unhealthy':
        return 'text-red-400';
      default:
        return 'text-muted-foreground';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle2 className="h-4 w-4 text-green-400" />;
      case 'degraded':
        return <AlertCircle className="h-4 w-4 text-yellow-400" />;
      case 'unhealthy':
        return <AlertCircle className="h-4 w-4 text-red-400" />;
      default:
        return <Activity className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <Card className="border-border/50 bg-card/50 backdrop-blur">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-lg">
          <span className="flex items-center gap-2">
            <Server className="h-5 w-5 text-primary" />
            System Overview
          </span>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Badge variant="outline" className="border-green-500/50 text-green-400">
                <Wifi className="mr-1 h-3 w-3" />
                Connected
              </Badge>
            ) : (
              <Badge variant="outline" className="border-red-500/50 text-red-400">
                <WifiOff className="mr-1 h-3 w-3" />
                Disconnected
              </Badge>
            )}
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8 text-red-400">
            <AlertCircle className="mb-2 h-8 w-8" />
            <p>Failed to load system health</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Overall Status */}
            <div className="flex items-center justify-between rounded-lg bg-background/50 p-4">
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{
                    scale: health?.status === 'healthy' ? [1, 1.1, 1] : 1,
                  }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className={cn(
                    'flex h-10 w-10 items-center justify-center rounded-full',
                    health?.status === 'healthy' && 'bg-green-500/20',
                    health?.status === 'degraded' && 'bg-yellow-500/20',
                    health?.status === 'unhealthy' && 'bg-red-500/20'
                  )}
                >
                  {getStatusIcon(health?.status || 'unknown')}
                </motion.div>
                <div>
                  <p className="text-sm text-muted-foreground">System Status</p>
                  <p className={cn('text-lg font-semibold capitalize', getStatusColor(health?.status || 'unknown'))}>
                    {health?.status || 'Unknown'}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Version</p>
                <p className="font-mono text-sm">{health?.version || 'N/A'}</p>
              </div>
            </div>

            {/* Component Status */}
            <div className="grid grid-cols-2 gap-3">
              {/* Database */}
              <div className="rounded-lg border border-border/50 bg-background/30 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Database</span>
                  {getStatusIcon(health?.components?.database?.status || 'unknown')}
                </div>
                <p className={cn('mt-1 text-sm font-medium capitalize', getStatusColor(health?.components?.database?.status || 'unknown'))}>
                  {health?.components?.database?.status || 'Unknown'}
                </p>
              </div>

              {/* Redis */}
              <div className="rounded-lg border border-border/50 bg-background/30 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Redis</span>
                  {getStatusIcon(health?.components?.redis?.status || 'unknown')}
                </div>
                <p className={cn('mt-1 text-sm font-medium capitalize', getStatusColor(health?.components?.redis?.status || 'unknown'))}>
                  {health?.components?.redis?.status || 'Unknown'}
                </p>
              </div>
            </div>

            {/* Last Updated */}
            <div className="text-center text-xs text-muted-foreground">
              Last updated: {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : 'N/A'}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
