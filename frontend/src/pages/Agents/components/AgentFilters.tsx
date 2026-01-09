import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { AgentStatus, AgentType } from '@/types/api.types';

interface AgentFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  statusFilter: AgentStatus | 'all';
  onStatusFilterChange: (value: AgentStatus | 'all') => void;
  typeFilter: AgentType | 'all';
  onTypeFilterChange: (value: AgentType | 'all') => void;
  onClearFilters: () => void;
}

const STATUSES: Array<{ value: AgentStatus | 'all'; label: string }> = [
  { value: 'all', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'idle', label: 'Idle' },
  { value: 'busy', label: 'Busy' },
  { value: 'offline', label: 'Offline' },
  { value: 'failed', label: 'Failed' },
  { value: 'starting', label: 'Starting' },
];

const TYPES: Array<{ value: AgentType | 'all'; label: string }> = [
  { value: 'all', label: 'All Types' },
  { value: 'orchestrator', label: 'Orchestrator' },
  { value: 'worker', label: 'Worker' },
  { value: 'specialist', label: 'Specialist' },
  { value: 'research', label: 'Research' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'coordinator', label: 'Coordinator' },
];

export function AgentFilters({
  search,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  typeFilter,
  onTypeFilterChange,
  onClearFilters,
}: AgentFiltersProps) {
  const hasFilters = search || statusFilter !== 'all' || typeFilter !== 'all';

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search agents..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-10 bg-background"
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Select value={statusFilter} onValueChange={(v) => onStatusFilterChange(v as AgentStatus | 'all')}>
          <SelectTrigger className="w-[140px] bg-background">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {STATUSES.map((status) => (
              <SelectItem key={status.value} value={status.value}>
                {status.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={typeFilter} onValueChange={(v) => onTypeFilterChange(v as AgentType | 'all')}>
          <SelectTrigger className="w-[140px] bg-background">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            {TYPES.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {hasFilters && (
          <Button variant="ghost" size="sm" onClick={onClearFilters}>
            <X className="mr-1 h-4 w-4" />
            Clear
          </Button>
        )}
      </div>

      {/* Active filters display */}
      {hasFilters && (
        <div className="flex flex-wrap gap-2 sm:hidden">
          {search && (
            <Badge variant="secondary" className="gap-1">
              Search: {search}
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() => onSearchChange('')}
              />
            </Badge>
          )}
          {statusFilter !== 'all' && (
            <Badge variant="secondary" className="gap-1 capitalize">
              {statusFilter}
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() => onStatusFilterChange('all')}
              />
            </Badge>
          )}
          {typeFilter !== 'all' && (
            <Badge variant="secondary" className="gap-1 capitalize">
              {typeFilter}
              <X
                className="h-3 w-3 cursor-pointer"
                onClick={() => onTypeFilterChange('all')}
              />
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
