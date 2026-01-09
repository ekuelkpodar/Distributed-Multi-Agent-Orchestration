import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Bot,
  Clock,
  Cpu,
  MoreVertical,
  Settings,
  Trash2,
  Eye,
} from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/common/StatusBadge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { formatRelativeTime, truncate } from '@/lib/utils';
import type { Agent } from '@/types/api.types';

interface AgentCardProps {
  agent: Agent;
  onTerminate: (agentId: string) => void;
  onUpdateStatus: (agentId: string, status: string) => void;
}

const TYPE_COLORS: Record<string, string> = {
  orchestrator: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  worker: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  specialist: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  research: 'bg-green-500/20 text-green-400 border-green-500/30',
  analysis: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  coordinator: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
};

export function AgentCard({ agent, onTerminate, onUpdateStatus }: AgentCardProps) {
  const navigate = useNavigate();

  const handleViewDetails = () => {
    navigate(`/agents/${agent.id}`);
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
    >
      <Card className="group relative border-border/50 bg-card/50 backdrop-blur transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5">
        {/* Status Indicator */}
        <div className="absolute right-4 top-4">
          <StatusBadge status={agent.status} showPulse size="sm" />
        </div>

        <CardHeader className="pb-3">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold truncate pr-20">{agent.name}</h3>
              <Badge
                variant="outline"
                className={`mt-1 text-xs capitalize ${TYPE_COLORS[agent.type] || ''}`}
              >
                {agent.type}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Agent Info */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Cpu className="h-4 w-4" />
              <span className="truncate">{agent.config.model}</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>{formatRelativeTime(agent.last_heartbeat)}</span>
            </div>
          </div>

          {/* Capabilities */}
          <div>
            <p className="text-xs text-muted-foreground mb-2">Capabilities</p>
            <div className="flex flex-wrap gap-1">
              {agent.capabilities.skills.slice(0, 3).map((skill) => (
                <Badge key={skill} variant="secondary" className="text-xs">
                  {truncate(skill, 15)}
                </Badge>
              ))}
              {agent.capabilities.skills.length > 3 && (
                <Badge variant="secondary" className="text-xs">
                  +{agent.capabilities.skills.length - 3}
                </Badge>
              )}
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-3 rounded-lg bg-background/50 p-3 text-center text-sm">
            <div>
              <p className="font-semibold">{agent.capabilities.max_concurrent_tasks}</p>
              <p className="text-xs text-muted-foreground">Max Tasks</p>
            </div>
            <div>
              <p className="font-semibold">{agent.config.timeout_seconds}s</p>
              <p className="text-xs text-muted-foreground">Timeout</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-border/50">
            <Button variant="outline" size="sm" onClick={handleViewDetails}>
              <Eye className="mr-1 h-3 w-3" />
              Details
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={handleViewDetails}>
                  <Eye className="mr-2 h-4 w-4" />
                  View Details
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onUpdateStatus(agent.id, 'idle')}>
                  <Settings className="mr-2 h-4 w-4" />
                  Set Idle
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => onTerminate(agent.id)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Terminate
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
