'use client';

import { motion } from 'framer-motion';
import { Star } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

const testimonials = [
  {
    quote:
      'We reduced our data processing time from hours to minutes. The distributed architecture handles our 10M daily transactions effortlessly.',
    author: 'Sarah Chen',
    role: 'CTO',
    company: 'DataFlow Inc',
    avatar: 'SC',
  },
  {
    quote:
      'The real-time monitoring and observability tools are game-changing. We have complete visibility into every agent and task.',
    author: 'Michael Rodriguez',
    role: 'VP Engineering',
    company: 'CloudScale',
    avatar: 'MR',
  },
  {
    quote:
      'Best-in-class developer experience. The APIs are intuitive, the docs are comprehensive, and we were in production within a week.',
    author: 'Emily Watson',
    role: 'Lead Developer',
    company: 'TechCorp',
    avatar: 'EW',
  },
];

export function TestimonialsSection() {
  return (
    <section className="py-24 bg-slate-900/50">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <Badge variant="gradient" className="mb-4">
            Testimonials
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Loved by developers and trusted by enterprises
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {testimonials.map((testimonial, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card className="p-8 h-full bg-slate-800/50 border-slate-700 hover:border-slate-600 transition-colors">
                {/* Stars */}
                <div className="flex items-center gap-1 mb-4">
                  {[...Array(5)].map((_, i) => (
                    <Star
                      key={i}
                      className="w-5 h-5 fill-yellow-400 text-yellow-400"
                    />
                  ))}
                </div>

                {/* Quote */}
                <blockquote className="text-lg mb-6 text-slate-300 leading-relaxed">
                  &ldquo;{testimonial.quote}&rdquo;
                </blockquote>

                {/* Author */}
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center font-bold text-white">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className="font-semibold text-white">
                      {testimonial.author}
                    </div>
                    <div className="text-sm text-slate-400">
                      {testimonial.role} at {testimonial.company}
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
