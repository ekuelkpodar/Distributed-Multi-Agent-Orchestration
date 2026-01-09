'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

const faqs = [
  {
    question: 'How does the free trial work?',
    answer:
      'Get started with a 14-day free trial of our Professional plan. No credit card required. Full access to all features with no limitations.',
  },
  {
    question: 'Can I change plans anytime?',
    answer:
      "Yes! Upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate any credits or charges.",
  },
  {
    question: 'What happens if I exceed my plan limits?',
    answer:
      "We'll notify you when you approach your limits. You can upgrade your plan or purchase add-ons. We never throttle or shut down your agents without notice.",
  },
  {
    question: 'Do you offer on-premise deployment?',
    answer:
      'Yes, our Enterprise plan includes options for on-premise, private cloud, or hybrid deployments with dedicated support.',
  },
  {
    question: 'What kind of support do you provide?',
    answer:
      'Starter plans get community support. Professional includes 24-hour SLA. Enterprise includes dedicated support engineers and custom SLAs.',
  },
  {
    question: 'Is my data secure?',
    answer:
      "Yes. We're SOC 2 Type II certified with end-to-end encryption. All data is encrypted at rest and in transit. We never train on your data.",
  },
];

export function FAQSection() {
  return (
    <section id="faq" className="py-24">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <Badge variant="gradient" className="mb-4">
            FAQ
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Frequently asked questions
          </h2>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto">
            Everything you need to know about the platform
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="max-w-3xl mx-auto"
        >
          <Accordion type="single" collapsible>
            {faqs.map((faq, index) => (
              <AccordionItem key={index} value={`item-${index}`}>
                <AccordionTrigger className="text-left">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent>{faq.answer}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <p className="text-slate-400 mb-4">Still have questions?</p>
          <Button variant="outline" asChild>
            <Link href="/contact">Contact Support</Link>
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
