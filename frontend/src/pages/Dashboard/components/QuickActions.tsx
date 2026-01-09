import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Send, RefreshCw, Settings2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import { useSubmitTask } from '@/features/tasks/hooks/useTasks';
import type { AgentType, TaskPriority } from '@/types/api.types';

export function QuickActions() {
  const navigate = useNavigate();
  const spawnAgent = useSpawnAgent();
  const submitTask = useSubmitTask();

  const [spawnDialogOpen, setSpawnDialogOpen] = useState(false);
  const [taskDialogOpen, setTaskDialogOpen] = useState(false);

  // Spawn agent form
  const [agentName, setAgentName] = useState('');
  const [agentType, setAgentType] = useState<AgentType>('worker');

  // Submit task form
  const [taskDescription, setTaskDescription] = useState('');
  const [taskPriority, setTaskPriority] = useState<TaskPriority>(3);

  const handleSpawnAgent = async () => {
    if (!agentName) return;

    try {
      await spawnAgent.mutateAsync({
        name: agentName,
        agent_type: agentType,
      });
      setSpawnDialogOpen(false);
      setAgentName('');
      setAgentType('worker');
    } catch (error) {
      console.error('Failed to spawn agent:', error);
    }
  };

  const handleSubmitTask = async () => {
    if (!taskDescription) return;

    try {
      await submitTask.mutateAsync({
        description: taskDescription,
        priority: taskPriority,
      });
      setTaskDialogOpen(false);
      setTaskDescription('');
      setTaskPriority(3);
    } catch (error) {
      console.error('Failed to submit task:', error);
    }
  };

  const actions = [
    {
      icon: Plus,
      label: 'Spawn Agent',
      description: 'Create a new agent',
      color: 'bg-purple-500/10 text-purple-400 hover:bg-purple-500/20',
      onClick: () => setSpawnDialogOpen(true),
    },
    {
      icon: Send,
      label: 'Submit Task',
      description: 'Add a new task',
      color: 'bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20',
      onClick: () => setTaskDialogOpen(true),
    },
    {
      icon: RefreshCw,
      label: 'View Agents',
      description: 'Manage agents',
      color: 'bg-blue-500/10 text-blue-400 hover:bg-blue-500/20',
      onClick: () => navigate('/agents'),
    },
    {
      icon: Settings2,
      label: 'Settings',
      description: 'Configure system',
      color: 'bg-gray-500/10 text-gray-400 hover:bg-gray-500/20',
      onClick: () => navigate('/settings'),
    },
  ];

  return (
    <>
      <Card className="border-border/50 bg-card/50 backdrop-blur">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3">
            {actions.map((action, index) => (
              <motion.button
                key={action.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                onClick={action.onClick}
                className={`flex flex-col items-center gap-2 rounded-lg border border-border/50 p-4 transition-colors ${action.color}`}
              >
                <action.icon className="h-6 w-6" />
                <span className="text-sm font-medium">{action.label}</span>
                <span className="text-xs text-muted-foreground">{action.description}</span>
              </motion.button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Spawn Agent Dialog */}
      <Dialog open={spawnDialogOpen} onOpenChange={setSpawnDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Spawn New Agent</DialogTitle>
            <DialogDescription>
              Create a new agent to handle tasks in the system.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="name" className="text-sm font-medium">
                Agent Name
              </label>
              <Input
                id="name"
                placeholder="e.g., ResearchAgent-01"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <label htmlFor="type" className="text-sm font-medium">
                Agent Type
              </label>
              <Select value={agentType} onValueChange={(v) => setAgentType(v as AgentType)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="worker">Worker</SelectItem>
                  <SelectItem value="research">Research</SelectItem>
                  <SelectItem value="analysis">Analysis</SelectItem>
                  <SelectItem value="specialist">Specialist</SelectItem>
                  <SelectItem value="coordinator">Coordinator</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSpawnDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSpawnAgent} disabled={spawnAgent.isPending || !agentName}>
              {spawnAgent.isPending ? 'Spawning...' : 'Spawn Agent'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Submit Task Dialog */}
      <Dialog open={taskDialogOpen} onOpenChange={setTaskDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit New Task</DialogTitle>
            <DialogDescription>
              Create a new task to be processed by available agents.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <label htmlFor="description" className="text-sm font-medium">
                Task Description
              </label>
              <Input
                id="description"
                placeholder="e.g., Research latest AI developments"
                value={taskDescription}
                onChange={(e) => setTaskDescription(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <label htmlFor="priority" className="text-sm font-medium">
                Priority
              </label>
              <Select
                value={String(taskPriority)}
                onValueChange={(v) => setTaskPriority(Number(v) as TaskPriority)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 - Critical</SelectItem>
                  <SelectItem value="2">2 - High</SelectItem>
                  <SelectItem value="3">3 - Medium</SelectItem>
                  <SelectItem value="4">4 - Low</SelectItem>
                  <SelectItem value="5">5 - Background</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTaskDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmitTask} disabled={submitTask.isPending || !taskDescription}>
              {submitTask.isPending ? 'Submitting...' : 'Submit Task'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
