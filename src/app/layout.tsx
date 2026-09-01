import type { Metadata } from 'next';
import { Inter, Geist } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/layout/providers';
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'Cirus — Cloud Incident Intelligence',
    template: '%s | Cirus',
  },
  description:
    'Upload a cloud incident report and generate enforceable guardrails, Terraform patches, alert rules, runbooks, and regression tests in minutes.',
  keywords: ['cloud incidents', 'post-mortem', 'SRE', 'DevOps', 'IaC', 'OPA', 'Terraform'],
  authors: [{ name: 'Cirus' }],
  openGraph: {
    type: 'website',
    title: 'Cirus — Cloud Incident Intelligence',
    description: 'Turn cloud incidents into automated prevention artifacts.',
    siteName: 'Cirus',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Cirus — Cloud Incident Intelligence',
    description: 'Turn cloud incidents into automated prevention artifacts.',
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={cn(inter.variable, "font-sans", geist.variable)} suppressHydrationWarning>
      <body className="bg-bg-base text-text-primary antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
