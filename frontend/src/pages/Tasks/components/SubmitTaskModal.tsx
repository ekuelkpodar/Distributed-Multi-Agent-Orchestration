import { useState } from 'react';
import { ListTodo, Plus, Send } from 'lucide-react';
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
import { useSubmitTask } from '@/features/tasks/hooks/useTasks';
import { useAgents } from '@/features/agents/hooks/useAgents';
import type { TaskPriority } from '@/types/api.types';

interface SubmitTaskModalProps {
  trigger?: React.ReactNode;
}

const PRIORITIES: Array<{ value: TaskPriority; label: string; description: string }> = [
  { value: 1, label: 'Critical', description: 'Urgent, immediate attention required' },
  { value: 2, label: 'High', description: 'Important, process soon' },
  { value: 3, label: 'Medium', description: 'Standard priority' },
  { value: 4, label: 'Low', description: 'Process when available' },
  { value: 5, label: 'Background', description: 'Process in spare capacity' },
];

export function SubmitTaskModal({ trigger }: SubmitTaskModalProps) {
  const [open, setOpen] = useState(false);
  const submitTask = useSubmitTask();
  const { data: agentsData } = useAgents({ status: 'idle' });

  // Form state
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<TaskPriority>(3);
  const [agentId, setAgentId] = useState<string>('');
  const [inputData, setInputData] = useState('');

  const handleSubmit = async () => {
    if (!description.trim()) return;

    try {
      let parsedInput: Record<string, unknown> = {};
      if (inputData.trim()) {
        try {
          parsedInput = JSON.parse(inputData);
        } catch {
          alert('Invalid JSON in input data');
          return;
        }
      }

      await submitTask.mutateAsync({
        description: description.trim(),
        priority,
        agent_id: agentId || undefined,
        input_data: parsedInput,
      });

      // Reset form and close
      setDescription('');
      setPriority(3);
      setAgentId('');
      setInputData('');
      setOpen(false);
    } catch (error) {
      console.error('Failed to submit task:', error);
    }
  };

  const availableAgents = agentsData?.agents.filter(
    (agent) => agent.status === 'idle' || agent.status === 'active'
  ) || [];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Submit Task
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ListTodo className="h-5 w-5 text-primary" />
            Submit New Task
          </DialogTitle>
          <DialogDescription>
            Create a new task to be processed by available agents. Tasks will be
            automatically assigned based on agent availability.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Description */}
          <div className="grid gap-2">
            <label htmlFor="description" className="text-sm font-medium">
              Task Description <span className="text-destructive">*</span>
            </label>
            <Input
              id="description"
              placeholder="e.g., Research the latest developments in quantum computing"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="bg-background"
            />
          </div>

          {/* Priority */}
          <div className="grid gap-2">
            <label htmlFor="priority" className="text-sm font-medium">
              Priority
            </label>
            <Select
              value={String(priority)}
              onValueChange={(v) => setPriority(Number(v) as TaskPriority)}
            >
              <SelectTrigger className="bg-background">
                <SelectValue placeholder="Select priority" />
              </SelectTrigger>
              <SelectContent>
                {PRIORITIES.map((p) => (
                  <SelectItem key={p.value} value={String(p.value)}>
                    <div className="flex flex-col">
                      <span>
                        {p.value} - {p.label}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {PRIORITIES.find((p) => p.value === priority)?.description}
            </p>
          </div>

          {/* Agent Assignment */}
          <div className="grid gap-2">
            <label htmlFor="agent" className="text-sm font-medium">
              Assign to Agent (Optional)
            </label>
            <Select value={agentId} onValueChange={setAgentId}>
              <SelectTrigger className="bg-background">
                <SelectValue placeholder="Auto-assign" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Auto-assign</SelectItem>
                {availableAgents.map((agent) => (
                  <SelectItem key={agent.id} value={agent.id}>
                    {agent.name} ({agent.type})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Leave empty to auto-assign to the best available agent
            </p>
          </div>

          {/* Input Data */}
          <div className="grid gap-2">
            <label htmlFor="inputData" className="text-sm font-medium">
              Input Data (Optional)
            </label>
            <textarea
              id="inputData"
              placeholder='{"key": "value"}'
              value={inputData}
              onChange={(e) => setInputData(e.target.value)}
              className="min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            <p className="text-xs text-muted-foreground">
              JSON format for additional task parameters
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitTask.isPending || !description.trim()}
          >
            {submitTask.isPending ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Submitting...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Submit Task
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
