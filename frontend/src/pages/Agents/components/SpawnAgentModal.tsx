import { useState } from 'react';
import { Bot, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useSpawnAgent } from '@/features/agents/hooks/useAgents';
import type { AgentType } from '@/types/api.types';

interface SpawnAgentModalProps {
  trigger?: React.ReactNode;
}

const AGENT_TYPES: { value: AgentType; label: string; description: string }[] = [
  { value: 'worker', label: 'Worker', description: 'General-purpose task execution' },
  { value: 'research', label: 'Research', description: 'Web research and information gathering' },
  { value: 'analysis', label: 'Analysis', description: 'Data analysis and processing' },
  { value: 'specialist', label: 'Specialist', description: 'Domain-specific expertise' },
  { value: 'coordinator', label: 'Coordinator', description: 'Task coordination and delegation' },
  { value: 'orchestrator', label: 'Orchestrator', description: 'High-level system management' },
];

const MODELS = [
  { value: 'anthropic/claude-3-haiku', label: 'Claude 3 Haiku (Fast)' },
  { value: 'anthropic/claude-3-sonnet', label: 'Claude 3 Sonnet (Balanced)' },
  { value: 'anthropic/claude-3-opus', label: 'Claude 3 Opus (Advanced)' },
  { value: 'openai/gpt-4-turbo', label: 'GPT-4 Turbo' },
  { value: 'openai/gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
];

export function SpawnAgentModal({ trigger }: SpawnAgentModalProps) {
  const [open, setOpen] = useState(false);
  const spawnAgent = useSpawnAgent();

  // Form state
  const [name, setName] = useState('');
  const [agentType, setAgentType] = useState<AgentType>('worker');
  const [model, setModel] = useState('anthropic/claude-3-haiku');
  const [capabilities, setCapabilities] = useState('');

  const handleSubmit = async () => {
    if (!name.trim()) return;

    try {
      await spawnAgent.mutateAsync({
        name: name.trim(),
        agent_type: agentType,
        model,
        capabilities: capabilities
          .split(',')
          .map((c) => c.trim())
          .filter(Boolean),
      });

      // Reset form and close
      setName('');
      setAgentType('worker');
      setModel('anthropic/claude-3-haiku');
      setCapabilities('');
      setOpen(false);
    } catch (error) {
      console.error('Failed to spawn agent:', error);
    }
  };

  const selectedTypeInfo = AGENT_TYPES.find((t) => t.value === agentType);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Spawn Agent
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            Spawn New Agent
          </DialogTitle>
          <DialogDescription>
            Create a new agent to join the orchestration system. Agents will
            automatically start and be available for task assignment.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Name */}
          <div className="grid gap-2">
            <label htmlFor="name" className="text-sm font-medium">
              Agent Name <span className="text-destructive">*</span>
            </label>
            <Input
              id="name"
              placeholder="e.g., ResearchAgent-01"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-background"
            />
          </div>

          {/* Type */}
          <div className="grid gap-2">
            <label htmlFor="type" className="text-sm font-medium">
              Agent Type
            </label>
            <Select value={agentType} onValueChange={(v) => setAgentType(v as AgentType)}>
              <SelectTrigger className="bg-background">
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                {AGENT_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div className="flex flex-col">
                      <span>{type.label}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedTypeInfo && (
              <p className="text-xs text-muted-foreground">
                {selectedTypeInfo.description}
              </p>
            )}
          </div>

          {/* Model */}
          <div className="grid gap-2">
            <label htmlFor="model" className="text-sm font-medium">
              LLM Model
            </label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="bg-background">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {MODELS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Capabilities */}
          <div className="grid gap-2">
            <label htmlFor="capabilities" className="text-sm font-medium">
              Additional Capabilities
            </label>
            <Input
              id="capabilities"
              placeholder="e.g., web-search, code-execution (comma-separated)"
              value={capabilities}
              onChange={(e) => setCapabilities(e.target.value)}
              className="bg-background"
            />
            <p className="text-xs text-muted-foreground">
              Optional: Comma-separated list of additional capabilities
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={spawnAgent.isPending || !name.trim()}
          >
            {spawnAgent.isPending ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Spawning...
              </>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" />
                Spawn Agent
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
