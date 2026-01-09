'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import {
  Zap,
  Globe,
  Shield,
  Activity,
  Layers,
  Code,
  Cpu,
  Database,
  ArrowRight,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

const features = [
  {
    icon: Zap,
    title: 'Real-time Coordination',
    description:
      'Agents communicate instantly with sub-50ms latency using event-driven architecture and WebSocket connections.',
  },
  {
    icon: Globe,
    title: 'Distributed by Design',
    description:
      'Deploy across multiple regions with automatic replication, failover, and load balancing for maximum reliability.',
  },
  {
    icon: Shield,
    title: 'Enterprise Security',
    description:
      'SOC 2 Type II certified with end-to-end encryption, RBAC, audit logs, and compliance with GDPR, HIPAA.',
  },
  {
    icon: Activity,
    title: 'Full Observability',
    description:
      'Distributed tracing, real-time metrics, and structured logging give you complete visibility into agent behavior.',
  },
  {
    icon: Layers,
    title: 'Intelligent Orchestration',
    description:
      'Automatic task decomposition, dependency resolution, and resource allocation powered by advanced algorithms.',
  },
  {
    icon: Code,
    title: 'Developer-First API',
    description:
      'RESTful APIs, WebSocket streams, gRPC services, and comprehensive SDKs for Python, JavaScript, and Go.',
  },
  {
    icon: Cpu,
    title: 'Auto-scaling',
    description:
      'Automatically scale agent pools based on workload with intelligent resource allocation and cost optimization.',
  },
  {
    icon: Database,
    title: 'Vector Memory',
    description:
      'Built-in vector database for semantic memory, context retrieval, and long-term knowledge retention.',
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="py-24 relative">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <Badge variant="gradient" className="mb-4">
            Features
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Enterprise-grade features
          </h2>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto">
            Built for scale, designed for developers. Everything you need to
            build, deploy, and manage production AI agent systems.
          </p>
        </motion.div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.05 }}
            >
              <Card className="p-6 h-full hover:bg-slate-800/80 transition-all hover:border-blue-500/50 group">
                <div className="text-blue-400 mb-4 group-hover:scale-110 transition-transform">
                  <feature.icon className="w-10 h-10" />
                </div>
                <h3 className="text-xl font-bold mb-3 text-white">
                  {feature.title}
                </h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <Button size="lg" variant="gradient" asChild>
            <Link href="/features">
              Explore All Features
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
