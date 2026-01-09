import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Bot,
  Clock,
  Cpu,
  Activity,
  Settings,
  Trash2,
  RefreshCw,
  Power,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/common/StatusBadge';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { EmptyState } from '@/components/common/EmptyState';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAgent, useTerminateAgent, useUpdateAgentStatus } from '@/features/agents/hooks/useAgents';
import { formatRelativeTime } from '@/lib/utils';

export default function AgentDetailsPage() {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();

  const { data: agent, isLoading, error } = useAgent(agentId || '');
  const terminateAgent = useTerminateAgent();
  const updateAgentStatus = useUpdateAgentStatus();

  const handleTerminate = async () => {
    if (!agentId) return;
    if (confirm('Are you sure you want to terminate this agent?')) {
      try {
        await terminateAgent.mutateAsync(agentId);
        navigate('/agents');
      } catch (error) {
        console.error('Failed to terminate agent:', error);
      }
    }
  };

  const handleUpdateStatus = async (status: string) => {
    if (!agentId) return;
    try {
      await updateAgentStatus.mutateAsync({ agentId, status });
    } catch (error) {
      console.error('Failed to update agent status:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <EmptyState
        icon={Bot}
        title="Agent not found"
        description="The agent you're looking for doesn't exist or has been terminated."
        action={
          <Button onClick={() => navigate('/agents')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Agents
          </Button>
        }
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/agents')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{agent.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className="capitalize">
                  {agent.type}
                </Badge>
                <StatusBadge status={agent.status} showPulse />
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => handleUpdateStatus('idle')}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Reset
          </Button>
          <Button variant="destructive" onClick={handleTerminate}>
            <Trash2 className="mr-2 h-4 w-4" />
            Terminate
          </Button>
        </div>
      </div>

      {/* Content */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="capabilities">Capabilities</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Basic Info */}
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg">Agent Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Agent ID</p>
                    <p className="font-mono text-sm">{agent.id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Type</p>
                    <p className="capitalize">{agent.type}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Created</p>
                    <p>{formatRelativeTime(agent.created_at)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Last Heartbeat</p>
                    <p>{formatRelativeTime(agent.last_heartbeat)}</p>
                  </div>
                </div>
                {agent.parent_id && (
                  <div>
                    <p className="text-sm text-muted-foreground">Parent Agent</p>
                    <p className="font-mono text-sm">{agent.parent_id}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Status Card */}
            <Card className="border-border/50 bg-card/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-lg">Current Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col items-center justify-center py-6">
                  <div className="relative">
                    <div className={`h-24 w-24 rounded-full ${
                      agent.status === 'active' ? 'bg-green-500/20' :
                      agent.status === 'busy' ? 'bg-yellow-500/20' :
                      agent.status === 'idle' ? 'bg-blue-500/20' :
                      'bg-gray-500/20'
                    } flex items-center justify-center`}>
                      <Activity className={`h-10 w-10 ${
                        agent.status === 'active' ? 'text-green-400' :
                        agent.status === 'busy' ? 'text-yellow-400' :
                        agent.status === 'idle' ? 'text-blue-400' :
                        'text-gray-400'
                      }`} />
                    </div>
                    {(agent.status === 'active' || agent.status === 'busy') && (
                      <span className="absolute -right-1 -top-1 flex h-4 w-4">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-4 w-4 bg-green-500" />
                      </span>
                    )}
                  </div>
                  <p className="mt-4 text-xl font-semibold capitalize">{agent.status}</p>
                  <p className="text-sm text-muted-foreground">
                    Last updated {formatRelativeTime(agent.updated_at)}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="capabilities" className="space-y-6">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Agent Capabilities</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <p className="text-sm font-medium mb-2">Skills</p>
                <div className="flex flex-wrap gap-2">
                  {agent.capabilities.skills.map((skill) => (
                    <Badge key={skill} variant="secondary">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Supported Task Types</p>
                <div className="flex flex-wrap gap-2">
                  {agent.capabilities.supported_task_types.map((type) => (
                    <Badge key={type} variant="outline">
                      {type}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Tools</p>
                <div className="flex flex-wrap gap-2">
                  {agent.capabilities.tools.map((tool) => (
                    <Badge key={tool} variant="outline" className="bg-purple-500/10 text-purple-400 border-purple-500/30">
                      {tool}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border/50">
                <div className="text-center p-4 rounded-lg bg-background/50">
                  <p className="text-2xl font-bold">{agent.capabilities.max_concurrent_tasks}</p>
                  <p className="text-sm text-muted-foreground">Max Concurrent Tasks</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config" className="space-y-6">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex items-center gap-3 p-4 rounded-lg bg-background/50">
                  <Cpu className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm text-muted-foreground">Model</p>
                    <p className="font-medium">{agent.config.model}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg bg-background/50">
                  <Settings className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm text-muted-foreground">Temperature</p>
                    <p className="font-medium">{agent.config.temperature}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg bg-background/50">
                  <Activity className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm text-muted-foreground">Max Tokens</p>
                    <p className="font-medium">{agent.config.max_tokens.toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg bg-background/50">
                  <Clock className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm text-muted-foreground">Timeout</p>
                    <p className="font-medium">{agent.config.timeout_seconds}s</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg bg-background/50">
                  <RefreshCw className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm text-muted-foreground">Retry Attempts</p>
                    <p className="font-medium">{agent.config.retry_attempts}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-lg bg-background/50">
                  <Power className="h-5 w-5 text-primary" />
                  <div>
                    <p className="text-sm text-muted-foreground">Memory</p>
                    <p className="font-medium">{agent.config.memory_enabled ? 'Enabled' : 'Disabled'}</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="text-lg">Recent Logs</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Activity className="mb-2 h-8 w-8" />
                <p>Log streaming coming soon</p>
                <p className="text-sm mt-1">Agent logs will appear here in real-time</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
