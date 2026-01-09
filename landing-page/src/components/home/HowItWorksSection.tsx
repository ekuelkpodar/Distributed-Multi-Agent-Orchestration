'use client';

import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';

const steps = [
  {
    number: 1,
    title: 'Define Agents',
    description: 'Configure specialized agents with unique capabilities and behavior',
    code: `const agent = await client.agents.spawn({
  type: 'research',
  capabilities: ['web_search', 'document_analysis'],
  config: {
    maxConcurrentTasks: 5,
    timeout: 300,
    model: 'claude-sonnet-4'
  }
});

console.log(\`Agent \${agent.id} ready\`);`,
  },
  {
    number: 2,
    title: 'Submit Tasks',
    description: 'Send work to the orchestrator with priorities and dependencies',
    code: `const task = await client.tasks.submit({
  description: 'Analyze Q4 financial trends',
  priority: 'high',
  agentType: 'research',
  context: {
    timeframe: 'Q4 2025',
    regions: ['NA', 'EU', 'APAC']
  }
});

console.log(\`Task \${task.id} submitted\`);`,
  },
  {
    number: 3,
    title: 'Monitor Execution',
    description: 'Watch agents work with real-time updates and live logs',
    code: `// Subscribe to real-time updates
client.tasks.subscribe(task.id, (event) => {
  console.log(\`Status: \${event.status}\`);
  console.log(\`Progress: \${event.progress}%\`);

  if (event.log) {
    console.log(\`Log: \${event.log}\`);
  }
});`,
  },
  {
    number: 4,
    title: 'Get Results',
    description: 'Retrieve structured outputs with metrics and audit trail',
    code: `const result = await client.tasks.getResult(task.id);

console.log(\`Status: \${result.status}\`);
console.log(\`Duration: \${result.duration}ms\`);
console.log(\`Output:\`, result.data);

// {
//   status: 'completed',
//   duration: 3240,
//   data: { insights: [...], metrics: {...} }
// }`,
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-24 bg-slate-900/50">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <Badge variant="gradient" className="mb-4">
            How It Works
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            From zero to production in minutes
          </h2>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto">
            Simple APIs and SDKs that feel natural. No complex configuration required.
          </p>
        </motion.div>

        <div className="max-w-4xl mx-auto">
          {steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.15 }}
              className="mb-12 last:mb-0"
            >
              <div className="flex gap-8">
                {/* Number Circle */}
                <div className="flex-shrink-0">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center text-2xl font-bold shadow-lg shadow-blue-500/25">
                    {step.number}
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-2xl md:text-3xl font-bold mb-3 text-white">
                    {step.title}
                  </h3>
                  <p className="text-slate-400 text-lg mb-6">{step.description}</p>

                  {/* Code Block */}
                  <div className="rounded-lg overflow-hidden border border-slate-700 bg-slate-900">
                    {/* Code Header */}
                    <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-800 bg-slate-800/50">
                      <div className="flex gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-red-500/60" />
                        <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                        <div className="w-3 h-3 rounded-full bg-green-500/60" />
                      </div>
                      <span className="text-xs text-slate-500 ml-2">
                        example.ts
                      </span>
                    </div>
                    {/* Code Content */}
                    <pre className="p-4 overflow-x-auto text-sm">
                      <code className="text-slate-300 font-mono whitespace-pre">
                        {step.code}
                      </code>
                    </pre>
                  </div>
                </div>
              </div>

              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div className="ml-8 h-12 w-0.5 bg-gradient-to-b from-blue-600 to-purple-600 opacity-30" />
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
