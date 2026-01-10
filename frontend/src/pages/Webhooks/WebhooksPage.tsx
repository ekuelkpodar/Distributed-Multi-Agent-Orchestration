import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Webhook,
  Plus,
  MoreVertical,
  CheckCircle,
  XCircle,
  Clock,
  Trash2,
  Edit,
  Play,
  Pause,
  RefreshCw,
  ExternalLink,
  Send,
  AlertTriangle,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// Types
interface WebhookConfig {
  id: string;
  name: string;
  url: string;
  events: string[];
  status: 'active' | 'paused' | 'disabled' | 'failed';
  created_at: string;
  updated_at: string;
  last_delivery_at: string | null;
  failure_count: number;
  success_count: number;
}

interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event_type: string;
  status: 'pending' | 'delivered' | 'failed' | 'retrying';
  attempt_count: number;
  created_at: string;
  delivered_at: string | null;
  response_status: number | null;
  duration_ms: number | null;
  error: string | null;
}

// Mock data
const mockWebhooks: WebhookConfig[] = [
  {
    id: 'wh-1',
    name: 'Slack Notifications',
    url: 'https://hooks.slack.com/services/xxx/yyy/zzz',
    events: ['task.completed', 'task.failed', 'agent.status_changed'],
    status: 'active',
    created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
    last_delivery_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    failure_count: 2,
    success_count: 1458,
  },
  {
    id: 'wh-2',
    name: 'Analytics Service',
    url: 'https://analytics.example.com/webhook',
    events: ['task.completed', 'task.created'],
    status: 'active',
    created_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    last_delivery_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    failure_count: 0,
    success_count: 3421,
  },
  {
    id: 'wh-3',
    name: 'Backup System',
    url: 'https://backup.internal/api/events',
    events: ['*'],
    status: 'paused',
    created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    last_delivery_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    failure_count: 0,
    success_count: 8923,
  },
  {
    id: 'wh-4',
    name: 'External Monitoring',
    url: 'https://monitoring.external.io/hooks/agent-ops',
    events: ['system.error', 'agent.error'],
    status: 'failed',
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    last_delivery_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    failure_count: 12,
    success_count: 156,
  },
];

const mockDeliveries: WebhookDelivery[] = [
  {
    id: 'del-1',
    webhook_id: 'wh-1',
    event_type: 'task.completed',
    status: 'delivered',
    attempt_count: 1,
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    delivered_at: new Date(Date.now() - 5 * 60 * 1000 + 234).toISOString(),
    response_status: 200,
    duration_ms: 234,
    error: null,
  },
  {
    id: 'del-2',
    webhook_id: 'wh-2',
    event_type: 'task.created',
    status: 'delivered',
    attempt_count: 1,
    created_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    delivered_at: new Date(Date.now() - 2 * 60 * 1000 + 156).toISOString(),
    response_status: 200,
    duration_ms: 156,
    error: null,
  },
  {
    id: 'del-3',
    webhook_id: 'wh-4',
    event_type: 'system.error',
    status: 'failed',
    attempt_count: 3,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    delivered_at: null,
    response_status: 502,
    duration_ms: 5000,
    error: 'Connection refused: ECONNREFUSED',
  },
];

const availableEvents = [
  { value: '*', label: 'All Events' },
  { value: 'agent.created', label: 'Agent Created' },
  { value: 'agent.updated', label: 'Agent Updated' },
  { value: 'agent.deleted', label: 'Agent Deleted' },
  { value: 'agent.status_changed', label: 'Agent Status Changed' },
  { value: 'task.created', label: 'Task Created' },
  { value: 'task.started', label: 'Task Started' },
  { value: 'task.completed', label: 'Task Completed' },
  { value: 'task.failed', label: 'Task Failed' },
  { value: 'system.error', label: 'System Error' },
  { value: 'system.alert', label: 'System Alert' },
];

export default function WebhooksPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedWebhook, setSelectedWebhook] = useState<string | null>(null);

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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">Active</Badge>;
      case 'paused':
        return <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">Paused</Badge>;
      case 'disabled':
        return <Badge className="bg-slate-500/10 text-slate-500 border-slate-500/20">Disabled</Badge>;
      case 'failed':
        return <Badge className="bg-red-500/10 text-red-500 border-red-500/20">Failed</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getDeliveryStatusBadge = (status: string) => {
    switch (status) {
      case 'delivered':
        return <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">Delivered</Badge>;
      case 'failed':
        return <Badge className="bg-red-500/10 text-red-500 border-red-500/20">Failed</Badge>;
      case 'retrying':
        return <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">Retrying</Badge>;
      case 'pending':
        return <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20">Pending</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const formatTimestamp = (timestamp: string | null) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  const totalDeliveries = mockWebhooks.reduce((sum, w) => sum + w.success_count + w.failure_count, 0);
  const totalSuccess = mockWebhooks.reduce((sum, w) => sum + w.success_count, 0);
  const successRate = totalDeliveries > 0 ? (totalSuccess / totalDeliveries) * 100 : 100;

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
          <h1 className="text-3xl font-bold tracking-tight">Webhooks</h1>
          <p className="text-muted-foreground">
            Manage webhook endpoints for event notifications
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Create Webhook
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Create Webhook</DialogTitle>
              <DialogDescription>
                Configure a new webhook endpoint to receive event notifications.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" placeholder="My Webhook" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="url">URL</Label>
                <Input id="url" placeholder="https://example.com/webhook" />
              </div>
              <div className="grid gap-2">
                <Label>Events</Label>
                <Select>
                  <SelectTrigger>
                    <SelectValue placeholder="Select events to subscribe" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableEvents.map((event) => (
                      <SelectItem key={event.value} value={event.value}>
                        {event.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => setIsCreateOpen(false)}>Create</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </motion.div>

      {/* Summary Cards */}
      <motion.div variants={itemVariants} className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Webhooks</p>
                <p className="text-2xl font-bold">{mockWebhooks.length}</p>
              </div>
              <Webhook className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active</p>
                <p className="text-2xl font-bold text-emerald-500">
                  {mockWebhooks.filter(w => w.status === 'active').length}
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-emerald-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Deliveries</p>
                <p className="text-2xl font-bold">{totalDeliveries.toLocaleString()}</p>
              </div>
              <Send className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Success Rate</p>
                <p className="text-2xl font-bold text-emerald-500">{successRate.toFixed(1)}%</p>
              </div>
              <div className="w-16">
                <Progress value={successRate} className="h-2" />
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Webhooks List */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle>Configured Webhooks</CardTitle>
            <CardDescription>
              Manage your webhook endpoints and monitor their status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockWebhooks.map((webhook) => (
                <div
                  key={webhook.id}
                  className={`border rounded-lg p-4 transition-colors ${
                    selectedWebhook === webhook.id ? 'border-primary bg-primary/5' : 'hover:border-primary/50'
                  }`}
                  onClick={() => setSelectedWebhook(selectedWebhook === webhook.id ? null : webhook.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className={`p-2 rounded-lg ${
                        webhook.status === 'active' ? 'bg-emerald-500/10' :
                        webhook.status === 'failed' ? 'bg-red-500/10' :
                        'bg-slate-500/10'
                      }`}>
                        <Webhook className={`h-5 w-5 ${
                          webhook.status === 'active' ? 'text-emerald-500' :
                          webhook.status === 'failed' ? 'text-red-500' :
                          'text-slate-500'
                        }`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">{webhook.name}</h3>
                          {getStatusBadge(webhook.status)}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1 font-mono truncate max-w-md">
                          {webhook.url}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <CheckCircle className="h-3 w-3 text-emerald-500" />
                            {webhook.success_count.toLocaleString()} delivered
                          </span>
                          {webhook.failure_count > 0 && (
                            <span className="flex items-center gap-1">
                              <XCircle className="h-3 w-3 text-red-500" />
                              {webhook.failure_count} failed
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            Last: {formatTimestamp(webhook.last_delivery_at)}
                          </span>
                        </div>
                      </div>
                    </div>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" onClick={(e) => e.stopPropagation()}>
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem className="gap-2">
                          <Send className="h-4 w-4" />
                          Send Test
                        </DropdownMenuItem>
                        <DropdownMenuItem className="gap-2">
                          <Edit className="h-4 w-4" />
                          Edit
                        </DropdownMenuItem>
                        {webhook.status === 'active' ? (
                          <DropdownMenuItem className="gap-2">
                            <Pause className="h-4 w-4" />
                            Pause
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem className="gap-2">
                            <Play className="h-4 w-4" />
                            Activate
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="gap-2 text-red-500">
                          <Trash2 className="h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  {selectedWebhook === webhook.id && (
                    <div className="mt-4 pt-4 border-t">
                      <div className="flex flex-wrap gap-2 mb-4">
                        <span className="text-sm text-muted-foreground">Subscribed events:</span>
                        {webhook.events.map((event) => (
                          <Badge key={event} variant="secondary" className="text-xs">
                            {event}
                          </Badge>
                        ))}
                      </div>
                      <h4 className="text-sm font-medium mb-2">Recent Deliveries</h4>
                      <div className="space-y-2">
                        {mockDeliveries
                          .filter(d => d.webhook_id === webhook.id)
                          .slice(0, 3)
                          .map((delivery) => (
                            <div key={delivery.id} className="flex items-center justify-between p-2 bg-muted/50 rounded text-sm">
                              <div className="flex items-center gap-2">
                                {getDeliveryStatusBadge(delivery.status)}
                                <span className="font-mono text-xs">{delivery.event_type}</span>
                              </div>
                              <div className="flex items-center gap-3 text-muted-foreground">
                                {delivery.response_status && (
                                  <span className={delivery.response_status >= 200 && delivery.response_status < 300 ? 'text-emerald-500' : 'text-red-500'}>
                                    HTTP {delivery.response_status}
                                  </span>
                                )}
                                {delivery.duration_ms && (
                                  <span>{delivery.duration_ms}ms</span>
                                )}
                                <span>{formatTimestamp(delivery.created_at)}</span>
                              </div>
                            </div>
                          ))}
                        {mockDeliveries.filter(d => d.webhook_id === webhook.id).length === 0 && (
                          <p className="text-sm text-muted-foreground text-center py-2">No recent deliveries</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
