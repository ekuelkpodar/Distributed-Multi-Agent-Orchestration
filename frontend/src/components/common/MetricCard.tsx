import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: LucideIcon | React.ReactNode;
  description?: string;
  trend?: number;
  trendLabel?: string;
  sparkline?: number[];
  loading?: boolean;
  className?: string;
  onClick?: () => void;
}

export function MetricCard({
  title,
  value,
  unit,
  icon: Icon,
  description,
  trend,
  trendLabel,
  sparkline,
  loading = false,
  className,
  onClick,
}: MetricCardProps) {
  const trendDirection = trend !== undefined ? (trend > 50 ? 'up' : trend < 50 ? 'down' : 'stable') : undefined;
  const TrendIcon = trendDirection === 'up' ? TrendingUp :
                    trendDirection === 'down' ? TrendingDown : Minus;

  const trendColor = trendDirection === 'up' ? 'text-emerald-400' :
                     trendDirection === 'down' ? 'text-red-400' : 'text-slate-400';

  const renderIcon = () => {
    if (!Icon) return null;
    if (typeof Icon === 'function') {
      return <Icon className="h-5 w-5" />;
    }
    return Icon;
  };

  if (loading) {
    return (
      <Card className={cn('p-6', className)}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-24 rounded bg-muted" />
          <div className="h-8 w-16 rounded bg-muted" />
        </div>
      </Card>
    );
  }

  return (
    <Card
      className={cn(
        'relative overflow-hidden p-6 transition-all hover:border-primary/50',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <div className="flex items-baseline gap-1">
            <motion.span
              key={String(value)}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-3xl font-bold tabular-nums tracking-tight"
            >
              {value}
            </motion.span>
            {unit && (
              <span className="text-sm text-muted-foreground">{unit}</span>
            )}
          </div>
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
          {trend !== undefined && trendLabel && (
            <div className={cn('flex items-center gap-1 text-xs', trendColor)}>
              <TrendIcon className="h-3 w-3" />
              <span>{trend}% {trendLabel}</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className="rounded-lg bg-primary/10 p-2 text-primary">
            {renderIcon()}
          </div>
        )}
      </div>

      {sparkline && sparkline.length > 0 && (
        <div className="mt-4 flex h-10 items-end gap-0.5">
          {sparkline.map((val, i) => {
            const max = Math.max(...sparkline);
            const height = max > 0 ? (val / max) * 100 : 0;
            return (
              <div
                key={i}
                className="flex-1 rounded-t bg-primary/30 transition-all hover:bg-primary/50"
                style={{ height: `${Math.max(height, 5)}%` }}
              />
            );
          })}
        </div>
      )}

      {/* Gradient accent */}
      <div className="absolute -bottom-1 -right-1 h-24 w-24 rounded-full bg-gradient-to-br from-primary/20 to-purple-500/20 blur-2xl" />
    </Card>
  );
}
