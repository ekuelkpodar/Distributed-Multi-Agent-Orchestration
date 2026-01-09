'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { ArrowRight, Play, Check, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const customerLogos = [
  { name: 'Company 1', initial: 'A' },
  { name: 'Company 2', initial: 'B' },
  { name: 'Company 3', initial: 'C' },
  { name: 'Company 4', initial: 'D' },
  { name: 'Company 5', initial: 'E' },
];

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Animated Grid Background */}
      <div className="absolute inset-0 bg-grid opacity-30" />

      {/* Gradient Orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute -top-1/4 -left-1/4 w-1/2 h-1/2 bg-blue-500/30 rounded-full blur-[120px]"
        />
        <motion.div
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 1,
          }}
          className="absolute -bottom-1/4 -right-1/4 w-1/2 h-1/2 bg-purple-500/30 rounded-full blur-[120px]"
        />
        <motion.div
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 2,
          }}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1/3 h-1/3 bg-cyan-500/20 rounded-full blur-[100px]"
        />
      </div>

      <div className="container mx-auto px-4 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="max-w-5xl mx-auto text-center"
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Badge variant="gradient" className="mb-6 px-4 py-1.5">
              <Sparkles className="w-3.5 h-3.5 mr-2" />
              Now in Public Beta - Start Free Today
            </Badge>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold mb-6 tracking-tight"
          >
            <span className="bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent">
              Orchestrate AI Agents
            </span>
            <br />
            <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
              at Scale
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="text-lg sm:text-xl md:text-2xl text-slate-300 mb-10 max-w-3xl mx-auto leading-relaxed"
          >
            Build, deploy, and manage distributed multi-agent systems with
            real-time coordination and enterprise reliability.{' '}
            <span className="text-blue-400 font-semibold">10x faster</span> than
            traditional workflows.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="flex flex-col sm:flex-row gap-4 justify-center mb-8"
          >
            <Button size="xl" variant="gradient" asChild>
              <Link href="/signup">
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button size="xl" variant="outline" asChild>
              <Link href="#demo">
                <Play className="mr-2 h-5 w-5" />
                Watch Demo
              </Link>
            </Button>
          </motion.div>

          {/* Trust Indicators */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400 mb-16"
          >
            <span className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-400" />
              No credit card required
            </span>
            <span className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-400" />
              14-day free trial
            </span>
            <span className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-400" />
              Cancel anytime
            </span>
          </motion.div>

          {/* Customer Logos */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.7 }}
          >
            <p className="text-sm text-slate-500 mb-6">
              Trusted by innovative teams worldwide
            </p>
            <div className="flex items-center justify-center gap-8 flex-wrap">
              {customerLogos.map((logo, index) => (
                <motion.div
                  key={logo.name}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8 + index * 0.1 }}
                  className="w-12 h-12 rounded-lg bg-slate-800/50 border border-slate-700 flex items-center justify-center text-slate-400 font-bold"
                >
                  {logo.initial}
                </motion.div>
              ))}
            </div>
          </motion.div>
        </motion.div>

        {/* Product Preview */}
        <motion.div
          initial={{ opacity: 0, y: 100 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.8 }}
          className="max-w-6xl mx-auto mt-20"
        >
          <div className="relative">
            {/* Glow Effect */}
            <div className="absolute inset-0 bg-gradient-to-t from-blue-500/20 via-purple-500/10 to-transparent rounded-xl blur-3xl" />

            {/* Dashboard Preview */}
            <div className="relative rounded-xl overflow-hidden border border-slate-700/50 shadow-2xl bg-slate-900">
              {/* Browser Chrome */}
              <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800 bg-slate-900/80">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80" />
                </div>
                <div className="flex-1 mx-4">
                  <div className="bg-slate-800 rounded-lg px-4 py-1.5 text-sm text-slate-400 max-w-md mx-auto">
                    app.agentops.io/dashboard
                  </div>
                </div>
              </div>

              {/* Dashboard Content Preview */}
              <div className="p-6 bg-gradient-to-br from-slate-900 to-slate-800">
                <div className="grid grid-cols-4 gap-4 mb-6">
                  {['Active Agents', 'Tasks Running', 'Avg Latency', 'Success Rate'].map(
                    (label, i) => (
                      <div
                        key={label}
                        className="bg-slate-800/50 rounded-lg p-4 border border-slate-700/50"
                      >
                        <div className="text-sm text-slate-400 mb-1">{label}</div>
                        <div className="text-2xl font-bold text-white">
                          {i === 0 ? '47' : i === 1 ? '234' : i === 2 ? '45ms' : '99.2%'}
                        </div>
                      </div>
                    )
                  )}
                </div>

                {/* Agent Network Visualization */}
                <div className="bg-slate-800/30 rounded-lg p-8 border border-slate-700/30 h-64 flex items-center justify-center relative overflow-hidden">
                  {/* Animated nodes */}
                  {[...Array(8)].map((_, i) => (
                    <motion.div
                      key={i}
                      animate={{
                        scale: [1, 1.2, 1],
                        opacity: [0.5, 1, 0.5],
                      }}
                      transition={{
                        duration: 2 + i * 0.5,
                        repeat: Infinity,
                        ease: 'easeInOut',
                        delay: i * 0.3,
                      }}
                      className="absolute w-4 h-4 rounded-full bg-gradient-to-r from-blue-500 to-purple-500"
                      style={{
                        left: `${15 + (i * 10)}%`,
                        top: `${20 + Math.sin(i) * 30}%`,
                      }}
                    />
                  ))}
                  <div className="text-slate-500 text-sm">
                    Real-time Agent Network Topology
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
