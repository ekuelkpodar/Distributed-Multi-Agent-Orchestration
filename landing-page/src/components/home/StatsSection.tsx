'use client';

import { motion } from 'framer-motion';
import { Zap, Users, Shield, Gauge, Rocket, DollarSign } from 'lucide-react';
import { Card } from '@/components/ui/card';

const stats = [
  {
    value: '10M+',
    label: 'Tasks Completed',
    description: 'AI agents have successfully processed millions of tasks',
    icon: Zap,
  },
  {
    value: '500K+',
    label: 'Agents Deployed',
    description: 'Across hundreds of organizations worldwide',
    icon: Users,
  },
  {
    value: '99.9%',
    label: 'Uptime SLA',
    description: 'Enterprise-grade reliability you can trust',
    icon: Shield,
  },
  {
    value: '45ms',
    label: 'Avg Latency',
    description: 'Lightning-fast agent coordination',
    icon: Gauge,
  },
  {
    value: '10x',
    label: 'Faster Execution',
    description: 'Compared to traditional sequential workflows',
    icon: Rocket,
  },
  {
    value: '50%',
    label: 'Cost Savings',
    description: 'Optimize resource usage with intelligent scheduling',
    icon: DollarSign,
  },
];

export function StatsSection() {
  return (
    <section className="py-24 bg-slate-900/50 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-grid opacity-20" />

      <div className="container mx-auto px-4 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold mb-4">
            Numbers that speak for themselves
          </h2>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Trusted by innovative teams building the future of AI
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {stats.map((stat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card className="p-8 hover:bg-slate-800/80 transition-all hover:border-blue-500/50 group">
                <div className="text-blue-400 mb-4 group-hover:scale-110 transition-transform">
                  <stat.icon className="w-10 h-10" />
                </div>
                <div className="text-5xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  {stat.value}
                </div>
                <div className="text-xl font-semibold mb-2 text-white">
                  {stat.label}
                </div>
                <p className="text-slate-400 text-sm">{stat.description}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
