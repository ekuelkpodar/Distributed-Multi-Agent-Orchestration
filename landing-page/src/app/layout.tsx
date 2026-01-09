import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: 'AgentOps Platform - Orchestrate AI Agents at Scale',
  description:
    'Build, deploy, and manage distributed multi-agent systems with real-time coordination and enterprise reliability. 10x faster than traditional workflows.',
  keywords: [
    'AI agents',
    'multi-agent systems',
    'orchestration',
    'distributed systems',
    'enterprise AI',
    'automation',
  ],
  authors: [{ name: 'AgentOps Platform' }],
  openGraph: {
    title: 'AgentOps Platform - Orchestrate AI Agents at Scale',
    description:
      'Build, deploy, and manage distributed multi-agent systems with real-time coordination and enterprise reliability.',
    url: 'https://agentops.io',
    siteName: 'AgentOps Platform',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'AgentOps Platform',
      },
    ],
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AgentOps Platform - Orchestrate AI Agents at Scale',
    description:
      'Build, deploy, and manage distributed multi-agent systems with real-time coordination and enterprise reliability.',
    images: ['/og-image.png'],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
