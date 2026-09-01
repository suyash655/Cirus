'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { spring } from '@/lib/motion/tokens';

export function NavHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Close mobile menu when clicking a link
  const handleLinkClick = () => {
    setMobileMenuOpen(false);
  };

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 lg:px-12 h-16 transition-all duration-300',
        scrolled ? 'bg-bg-base/90 border-b border-border-base backdrop-blur-md' : 'bg-transparent border-b border-transparent'
      )}
    >
      <Link href="/" className="flex items-center gap-2 group" id="nav-logo" onClick={handleLinkClick}>
        <span className="text-base font-bold tracking-tight text-text-primary">Cirus</span>
      </Link>

      {/* Desktop Navigation */}
      <nav className="hidden md:flex items-center gap-8" aria-label="Main navigation">
        {[
          { label: 'Problem', href: '#problem' },
          { label: 'How it works', href: '#workflow' },
          { label: 'Features', href: '#features' },
          { label: 'Compare', href: '#compare' },
        ].map((item) => (
          <Link
            key={item.label}
            href={item.href}
            className="text-sm font-medium text-text-muted hover:text-text-primary transition-colors"
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="flex items-center gap-4">
        <Link 
          href="/dashboard" 
          id="nav-dashboard-link" 
          className="text-sm font-medium text-text-primary hover:text-text-secondary transition-colors hidden md:block"
        >
          Sign in
        </Link>
        <Link href="/incidents/new" id="nav-cta-btn" className="hidden md:block">
          <motion.button
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.98 }}
            transition={spring.tactile}
            className="inline-flex items-center justify-center text-sm font-semibold h-9 px-4 rounded-lg bg-inverse-bg text-inverse-text transition-colors hover:opacity-90"
          >
            Analyze Incident
          </motion.button>
        </Link>

        {/* Mobile Menu Button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 rounded-lg hover:bg-bg-surface transition-colors"
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? <X className="w-5 h-5 text-text-primary" /> : <Menu className="w-5 h-5 text-text-primary" />}
        </button>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="absolute top-16 left-0 right-0 bg-bg-base border-b border-border-base md:hidden"
          >
            <nav className="flex flex-col p-6 gap-4" aria-label="Mobile navigation">
              {[
                { label: 'Problem', href: '#problem' },
                { label: 'How it works', href: '#workflow' },
                { label: 'Features', href: '#features' },
                { label: 'Compare', href: '#compare' },
              ].map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={handleLinkClick}
                  className="text-base font-medium text-text-primary hover:text-text-secondary transition-colors py-2"
                >
                  {item.label}
                </Link>
              ))}
              <div className="h-px bg-border-dim my-2" />
              <Link
                href="/dashboard"
                onClick={handleLinkClick}
                className="text-base font-medium text-text-primary hover:text-text-secondary transition-colors py-2"
              >
                Sign in
              </Link>
              <Link href="/incidents/new" onClick={handleLinkClick}>
                <motion.button
                  whileTap={{ scale: 0.98 }}
                  transition={spring.tactile}
                  className="w-full inline-flex items-center justify-center text-sm font-semibold h-11 px-6 rounded-lg bg-inverse-bg text-inverse-text transition-colors hover:opacity-90"
                >
                  Analyze Incident
                </motion.button>
              </Link>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
