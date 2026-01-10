import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Search,
  Filter,
  Download,
  Clock,
  User,
  Bot,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  FileText,
  Activity,
  Shield,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// Types
interface AuditEntry {
  id: string;
  event_type: string;
  timestamp: string;
  actor_id: string | null;
  actor_type: string;
  resource_type: string | null;
  resource_id: string | null;
  action: string;
  details: Record<string, unknown>;
  success: boolean;
  error_message: string | null;
  ip_address: string | null;
}

interface AuditSummary {
  total_events: number;
  events_by_type: Record<string, number>;
  success_rate: number;
}

// Mock data
const mockAuditEntries: AuditEntry[] = [
  {
    id: '1',
    event_type: 'agent.created',
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    actor_id: 'user-123',
    actor_type: 'user',
    resource_type: 'agent',
    resource_id: 'agent-abc',
    action: "Created agent 'ResearchBot' of type 'research'",
    details: { agent_name: 'ResearchBot', agent_type: 'research' },
    success: true,
    error_message: null,
    ip_address: '192.168.1.100',
  },
  {
    id: '2',
    event_type: 'task.completed',
    timestamp: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
    actor_id: 'agent-xyz',
    actor_type: 'agent',
    resource_type: 'task',
    resource_id: 'task-456',
    action: 'Task completed by agent in 2340ms',
    details: { duration_ms: 2340 },
    success: true,
    error_message: null,
    ip_address: null,
  },
  {
    id: '3',
    event_type: 'task.failed',
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    actor_id: 'agent-def',
    actor_type: 'agent',
    resource_type: 'task',
    resource_id: 'task-789',
    action: 'Task failed',
    details: { error: 'Connection timeout to external API' },
    success: false,
    error_message: 'Connection timeout to external API',
    ip_address: null,
  },
  {
    id: '4',
    event_type: 'auth.login',
    timestamp: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
    actor_id: 'user-456',
    actor_type: 'user',
    resource_type: 'session',
    resource_id: 'sess-123',
    action: 'User logged in',
    details: {},
    success: true,
    error_message: null,
    ip_address: '10.0.0.50',
  },
  {
    id: '5',
    event_type: 'agent.status_changed',
    timestamp: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
    actor_id: 'system',
    actor_type: 'system',
    resource_type: 'agent',
    resource_id: 'agent-ghi',
    action: "Agent status changed from 'active' to 'idle'",
    details: { old_status: 'active', new_status: 'idle' },
    success: true,
    error_message: null,
    ip_address: null,
  },
  {
    id: '6',
    event_type: 'auth.failed',
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    actor_id: 'unknown',
    actor_type: 'user',
    resource_type: 'session',
    resource_id: null,
    action: 'Login attempt failed',
    details: { reason: 'Invalid credentials' },
    success: false,
    error_message: 'Invalid credentials',
    ip_address: '203.0.113.42',
  },
];

const mockSummary: AuditSummary = {
  total_events: 12547,
  events_by_type: {
    'task.completed': 8432,
    'task.created': 2341,
    'agent.created': 156,
    'agent.status_changed': 892,
    'auth.login': 423,
    'task.failed': 203,
    'auth.failed': 100,
  },
  success_rate: 97.4,
};

export default function AuditLogPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('all');
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null);

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

  const getEventIcon = (eventType: string) => {
    if (eventType.startsWith('agent')) return <Bot className="h-4 w-4" />;
    if (eventType.startsWith('task')) return <FileText className="h-4 w-4" />;
    if (eventType.startsWith('auth')) return <Shield className="h-4 w-4" />;
    if (eventType.startsWith('system')) return <Activity className="h-4 w-4" />;
    return <Info className="h-4 w-4" />;
  };

  const getEventColor = (eventType: string, success: boolean) => {
    if (!success) return 'bg-red-500/10 text-red-500 border-red-500/20';
    if (eventType.includes('created')) return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
    if (eventType.includes('deleted') || eventType.includes('failed')) return 'bg-red-500/10 text-red-500 border-red-500/20';
    if (eventType.includes('updated') || eventType.includes('changed')) return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    return 'bg-slate-500/10 text-slate-500 border-slate-500/20';
  };

  const formatTimestamp = (timestamp: string) => {
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

  const filteredEntries = mockAuditEntries.filter((entry) => {
    if (eventTypeFilter !== 'all' && !entry.event_type.startsWith(eventTypeFilter)) {
      return false;
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        entry.action.toLowerCase().includes(query) ||
        entry.event_type.toLowerCase().includes(query) ||
        entry.resource_id?.toLowerCase().includes(query) ||
        entry.actor_id?.toLowerCase().includes(query)
      );
    }
    return true;
  });

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
          <h1 className="text-3xl font-bold tracking-tight">Audit Log</h1>
          <p className="text-muted-foreground">
            Complete audit trail of all system events and activities
          </p>
        </div>
        <Button variant="outline" className="gap-2">
          <Download className="h-4 w-4" />
          Export
        </Button>
      </motion.div>

      {/* Summary Cards */}
      <motion.div variants={itemVariants} className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Events</p>
                <p className="text-2xl font-bold">{mockSummary.total_events.toLocaleString()}</p>
              </div>
              <FileText className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Success Rate</p>
                <p className="text-2xl font-bold text-emerald-500">{mockSummary.success_rate}%</p>
              </div>
              <CheckCircle className="h-8 w-8 text-emerald-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Failed Events</p>
                <p className="text-2xl font-bold text-red-500">
                  {Math.round(mockSummary.total_events * (100 - mockSummary.success_rate) / 100)}
                </p>
              </div>
              <XCircle className="h-8 w-8 text-red-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Event Types</p>
                <p className="text-2xl font-bold">{Object.keys(mockSummary.events_by_type).length}</p>
              </div>
              <Activity className="h-8 w-8 text-muted-foreground/50" />
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Filters and Search */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-4">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search events..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Select value={eventTypeFilter} onValueChange={setEventTypeFilter}>
                <SelectTrigger className="w-[180px]">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Event type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Events</SelectItem>
                  <SelectItem value="agent">Agent Events</SelectItem>
                  <SelectItem value="task">Task Events</SelectItem>
                  <SelectItem value="auth">Auth Events</SelectItem>
                  <SelectItem value="system">System Events</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Audit Entries */}
      <motion.div variants={itemVariants}>
        <Card>
          <CardHeader>
            <CardTitle>Recent Events</CardTitle>
            <CardDescription>
              Showing {filteredEntries.length} events
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[500px]">
              <div className="space-y-2">
                {filteredEntries.map((entry) => (
                  <div
                    key={entry.id}
                    className="border rounded-lg overflow-hidden"
                  >
                    <div
                      className="flex items-center gap-4 p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => setExpandedEntry(expandedEntry === entry.id ? null : entry.id)}
                    >
                      <div className={`p-2 rounded-lg ${getEventColor(entry.event_type, entry.success)}`}>
                        {entry.success ? getEventIcon(entry.event_type) : <XCircle className="h-4 w-4" />}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {entry.event_type}
                          </Badge>
                          {!entry.success && (
                            <Badge variant="destructive" className="text-xs">
                              Failed
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm mt-1 truncate">{entry.action}</p>
                      </div>

                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        {entry.actor_id && (
                          <div className="flex items-center gap-1">
                            {entry.actor_type === 'user' ? (
                              <User className="h-3 w-3" />
                            ) : entry.actor_type === 'agent' ? (
                              <Bot className="h-3 w-3" />
                            ) : (
                              <Activity className="h-3 w-3" />
                            )}
                            <span className="max-w-[100px] truncate">{entry.actor_id}</span>
                          </div>
                        )}
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatTimestamp(entry.timestamp)}
                        </div>
                        {expandedEntry === entry.id ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </div>
                    </div>

                    {expandedEntry === entry.id && (
                      <div className="border-t bg-muted/30 p-4">
                        <div className="grid gap-4 md:grid-cols-2">
                          <div>
                            <h4 className="text-sm font-medium mb-2">Event Details</h4>
                            <dl className="text-sm space-y-1">
                              <div className="flex justify-between">
                                <dt className="text-muted-foreground">Event ID:</dt>
                                <dd className="font-mono">{entry.id}</dd>
                              </div>
                              <div className="flex justify-between">
                                <dt className="text-muted-foreground">Timestamp:</dt>
                                <dd>{new Date(entry.timestamp).toLocaleString()}</dd>
                              </div>
                              {entry.resource_type && (
                                <div className="flex justify-between">
                                  <dt className="text-muted-foreground">Resource:</dt>
                                  <dd>{entry.resource_type}/{entry.resource_id}</dd>
                                </div>
                              )}
                              {entry.ip_address && (
                                <div className="flex justify-between">
                                  <dt className="text-muted-foreground">IP Address:</dt>
                                  <dd className="font-mono">{entry.ip_address}</dd>
                                </div>
                              )}
                            </dl>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium mb-2">Additional Data</h4>
                            <pre className="text-xs bg-background p-2 rounded overflow-auto max-h-[100px]">
                              {JSON.stringify(entry.details, null, 2)}
                            </pre>
                            {entry.error_message && (
                              <div className="mt-2 p-2 bg-red-500/10 rounded border border-red-500/20">
                                <p className="text-xs text-red-500">{entry.error_message}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
