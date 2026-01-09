'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { Check } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const plans = [
  {
    name: 'Starter',
    price: 'Free',
    period: '',
    description: 'Perfect for side projects and experimentation',
    features: [
      'Up to 5 agents',
      '1,000 tasks/month',
      'Community support',
      'Basic observability',
      '14-day retention',
    ],
    cta: 'Start Free',
    href: '/signup',
    popular: false,
  },
  {
    name: 'Professional',
    price: '$299',
    period: '/month',
    description: 'For teams building production applications',
    features: [
      'Unlimited agents',
      '100,000 tasks/month',
      'Priority support (24h SLA)',
      'Advanced observability',
      '90-day retention',
      'SSO & RBAC',
      'SLA guarantee',
    ],
    cta: 'Start Free Trial',
    href: '/signup?plan=professional',
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For organizations with advanced needs',
    features: [
      'Unlimited everything',
      'Dedicated infrastructure',
      'White-glove support',
      'Custom integrations',
      'Unlimited retention',
      'On-premise deployment',
      'Custom SLA',
    ],
    cta: 'Contact Sales',
    href: '/contact',
    popular: false,
  },
];

export function PricingSection() {
  return (
    <section id="pricing" className="py-24">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <Badge variant="gradient" className="mb-4">
            Pricing
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Simple, transparent pricing
          </h2>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto">
            Start free, scale as you grow. No hidden fees, no surprises.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {plans.map((plan, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className={cn('relative', plan.popular && 'md:-mt-4 md:scale-105')}
            >
              {plan.popular && (
                <Badge className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-blue-600 to-purple-600 border-0 z-10">
                  Most Popular
                </Badge>
              )}

              <Card
                className={cn(
                  'p-8 h-full flex flex-col',
                  plan.popular
                    ? 'bg-gradient-to-b from-slate-800 to-slate-900 border-blue-500/50 shadow-lg shadow-blue-500/10'
                    : 'bg-slate-800/50 border-slate-700'
                )}
              >
                <div>
                  <h3 className="text-2xl font-bold mb-2 text-white">
                    {plan.name}
                  </h3>
                  <p className="text-slate-400 text-sm mb-6">
                    {plan.description}
                  </p>

                  <div className="mb-6">
                    <span className="text-5xl font-bold text-white">
                      {plan.price}
                    </span>
                    {plan.period && (
                      <span className="text-slate-400 text-lg">{plan.period}</span>
                    )}
                  </div>

                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-3">
                        <Check className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                        <span className="text-slate-300">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <Button
                  className={cn(
                    'w-full mt-auto',
                    plan.popular ? 'bg-gradient-to-r from-blue-600 to-purple-600' : ''
                  )}
                  variant={plan.popular ? 'default' : 'outline'}
                  asChild
                >
                  <Link href={plan.href}>{plan.cta}</Link>
                </Button>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* FAQ Link */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <p className="text-slate-400 mb-4">Have questions about pricing?</p>
          <Button variant="link" asChild>
            <Link href="#faq">View FAQ →</Link>
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
