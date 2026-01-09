import { cn } from '@/lib/utils';

type Status = 'active' | 'idle' | 'busy' | 'offline' | 'failed' | 'pending' | 'running' | 'completed' | 'queued' | 'starting' | 'cancelled';

interface StatusBadgeProps {
  status: Status | string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  pulse?: boolean;
  className?: string;
}

const statusConfig: Record<Status, { color: string; bg: string; label: string }> = {
  active: {
    color: 'bg-emerald-500',
    bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    label: 'Active',
  },
  idle: {
    color: 'bg-slate-400',
    bg: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
    label: 'Idle',
  },
  busy: {
    color: 'bg-amber-500',
    bg: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    label: 'Busy',
  },
  offline: {
    color: 'bg-slate-600',
    bg: 'bg-slate-600/20 text-slate-500 border-slate-600/30',
    label: 'Offline',
  },
  failed: {
    color: 'bg-red-500',
    bg: 'bg-red-500/20 text-red-400 border-red-500/30',
    label: 'Failed',
  },
  pending: {
    color: 'bg-slate-400',
    bg: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
    label: 'Pending',
  },
  running: {
    color: 'bg-cyan-500',
    bg: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    label: 'Running',
  },
  completed: {
    color: 'bg-emerald-500',
    bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    label: 'Completed',
  },
  queued: {
    color: 'bg-purple-500',
    bg: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    label: 'Queued',
  },
  starting: {
    color: 'bg-blue-500',
    bg: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    label: 'Starting',
  },
  cancelled: {
    color: 'bg-gray-500',
    bg: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    label: 'Cancelled',
  },
};

const sizeClasses = {
  sm: 'w-2 h-2',
  md: 'w-2.5 h-2.5',
  lg: 'w-3 h-3',
};

export function StatusBadge({
  status,
  size = 'md',
  showLabel = false,
  showPulse = false,
  className,
}: StatusBadgeProps & { showPulse?: boolean }) {
  const pulse = showPulse;
  const config = statusConfig[status as Status] || statusConfig.offline;
  const shouldPulse = pulse && ['active', 'running', 'busy'].includes(status);

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-full border px-2.5 py-0.5',
        config.bg,
        className
      )}
    >
      <span className="relative flex">
        <span
          className={cn(
            'rounded-full',
            config.color,
            sizeClasses[size]
          )}
        />
        {shouldPulse && (
          <span
            className={cn(
              'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
              config.color
            )}
          />
        )}
      </span>
      {showLabel && (
        <span className="text-xs font-medium">{config.label}</span>
      )}
    </div>
  );
}
