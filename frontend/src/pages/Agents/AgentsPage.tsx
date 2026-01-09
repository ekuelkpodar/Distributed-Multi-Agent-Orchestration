import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Grid3X3, List } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/common/EmptyState';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { useAgents, useTerminateAgent, useUpdateAgentStatus } from '@/features/agents/hooks/useAgents';
import { AgentCard } from './components/AgentCard';
import { AgentFilters } from './components/AgentFilters';
import { SpawnAgentModal } from './components/SpawnAgentModal';
import type { AgentStatus, AgentType } from '@/types/api.types';

type ViewMode = 'grid' | 'list';

export default function AgentsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<AgentStatus | 'all'>('all');
  const [typeFilter, setTypeFilter] = useState<AgentType | 'all'>('all');

  const { data, isLoading, error } = useAgents();
  const terminateAgent = useTerminateAgent();
  const updateAgentStatus = useUpdateAgentStatus();

  // Filter agents
  const filteredAgents = useMemo(() => {
    if (!data?.agents) return [];

    return data.agents.filter((agent) => {
      // Search filter
      if (search) {
        const searchLower = search.toLowerCase();
        const matchesSearch =
          agent.name.toLowerCase().includes(searchLower) ||
          agent.id.toLowerCase().includes(searchLower) ||
          agent.type.toLowerCase().includes(searchLower);
        if (!matchesSearch) return false;
      }

      // Status filter
      if (statusFilter !== 'all' && agent.status !== statusFilter) {
        return false;
      }

      // Type filter
      if (typeFilter !== 'all' && agent.type !== typeFilter) {
        return false;
      }

      return true;
    });
  }, [data?.agents, search, statusFilter, typeFilter]);

  const handleClearFilters = () => {
    setSearch('');
    setStatusFilter('all');
    setTypeFilter('all');
  };

  const handleTerminate = async (agentId: string) => {
    if (confirm('Are you sure you want to terminate this agent?')) {
      try {
        await terminateAgent.mutateAsync(agentId);
      } catch (error) {
        console.error('Failed to terminate agent:', error);
      }
    }
  };

  const handleUpdateStatus = async (agentId: string, status: string) => {
    try {
      await updateAgentStatus.mutateAsync({ agentId, status });
    } catch (error) {
      console.error('Failed to update agent status:', error);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05,
      },
    },
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground">
            Manage and monitor your AI agents
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* View Toggle */}
          <div className="flex items-center rounded-lg border border-border bg-background p-1">
            <Button
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              size="icon"
              className="h-8 w-8"
              onClick={() => setViewMode('grid')}
            >
              <Grid3X3 className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              className="h-8 w-8"
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
          <SpawnAgentModal />
        </div>
      </div>

      {/* Filters */}
      <AgentFilters
        search={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        onClearFilters={handleClearFilters}
      />

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : error ? (
        <EmptyState
          icon={Bot}
          title="Failed to load agents"
          description="There was an error loading the agents. Please try again."
          action={
            <Button onClick={() => window.location.reload()}>
              Retry
            </Button>
          }
        />
      ) : filteredAgents.length === 0 ? (
        <EmptyState
          icon={Bot}
          title={data?.agents?.length === 0 ? 'No agents yet' : 'No agents found'}
          description={
            data?.agents?.length === 0
              ? 'Spawn your first agent to get started with task execution.'
              : 'Try adjusting your filters to find agents.'
          }
          action={
            data?.agents?.length === 0 ? (
              <SpawnAgentModal />
            ) : (
              <Button variant="outline" onClick={handleClearFilters}>
                Clear Filters
              </Button>
            )
          }
        />
      ) : (
        <>
          {/* Stats Bar */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>
              Showing <strong className="text-foreground">{filteredAgents.length}</strong> of{' '}
              <strong className="text-foreground">{data?.total ?? 0}</strong> agents
            </span>
          </div>

          {/* Agent Grid/List */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className={
              viewMode === 'grid'
                ? 'grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
                : 'space-y-4'
            }
          >
            <AnimatePresence mode="popLayout">
              {filteredAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  onTerminate={handleTerminate}
                  onUpdateStatus={handleUpdateStatus}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        </>
      )}
    </div>
  );
}
