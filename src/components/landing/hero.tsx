'use client';

import React, { useRef, useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { motion, useMotionValue, useSpring, AnimatePresence } from 'framer-motion';
import { ArrowRight, Play, Shield, FileCode2, Bell, BookOpen, Check, Zap, Users, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ease, duration, spring, fadeUp } from '@/lib/motion/tokens';
import { Reveal, StaggerGroup } from './motion-primitives';

// ─── Pipeline stage data ──────────────────────────────────────────────────────
const PIPELINE_STAGES = [
  { id: 'input',    label: 'Incident Input',      icon: '📋' },
  { id: 'norm',     label: 'Normalization',       icon: '⚡' },
  { id: 'rca',      label: 'Root Cause',          icon: '🔍' },
  { id: 'context',  label: 'Context Retrieval',   icon: '🧠' },
  { id: 'gen',      label: 'Guardrail Gen',       icon: '🛡️' },
  { id: 'approve',  label: 'Human Approval',      icon: '✅' },
] as const;

const ARTIFACTS = [
  { icon: Shield,   label: 'OPA Policy'      },
  { icon: FileCode2,label: 'Terraform Patch' },
  { icon: Bell,     label: 'Alert Rule'      },
  { icon: BookOpen, label: 'Runbook'         },
] as const;

const STAT_CHIPS = [
  { icon: Zap,         label: '< 2 min',    sub: 'per incident'  },
  { icon: TrendingUp,  label: '94%',        sub: 'accuracy'      },
  { icon: Users,       label: '500+',       sub: 'teams using'   },
  { icon: Check,       label: '6 artifacts',sub: 'auto-generated'},
];

// ─── Animated pipeline node ───────────────────────────────────────────────────
function PipelineNode({
  stage, index, activeStage,
}: {
  stage: typeof PIPELINE_STAGES[number];
  index: number;
  activeStage: number;
}) {
  const isDone    = index < activeStage;
  const isActive  = index === activeStage;
  const isPending = index > activeStage;

  return (
    <div className="relative flex items-center gap-3">
      {/* Node circle */}
      <div className="relative flex-shrink-0 z-10">
        <motion.div
          layout
          initial={false}
          animate={{
            backgroundColor: isDone ? 'hsl(var(--inverse-bg))' : isActive ? 'hsl(191 100% 52%)' : 'hsl(var(--bg-raised))',
            borderColor: isDone ? 'hsl(var(--inverse-bg))' : isActive ? 'hsl(191 100% 52%)' : 'hsl(var(--border-base))',
            color: (isDone || isActive) ? 'hsl(var(--inverse-text))' : 'hsl(var(--text-muted))',
            scale: isActive ? 1.05 : 1,
          }}
          transition={spring.card}
          className="w-7 h-7 rounded-full flex items-center justify-center text-xs border bg-surface z-10 relative"
        >
          {isDone ? (
            <Check className="w-3.5 h-3.5 text-white" />
          ) : (
            <span className={cn('text-[10px]', isPending && 'opacity-60')}>
              {stage.icon}
            </span>
          )}
        </motion.div>
      </div>

      {/* Label */}
      <span
        className={cn(
          'text-[13px] font-medium transition-colors duration-300',
          isDone    && 'text-text-muted',
          isActive  && 'text-text-primary',
          isPending && 'text-text-faint',
        )}
      >
        {stage.label}
      </span>
      
      {/* Line connecting to next node */}
      {index < PIPELINE_STAGES.length - 1 && (
        <div className="absolute left-[13px] top-7 bottom-[-10px] w-px bg-border-dim -z-0" />
      )}
    </div>
  );
}

// ─── Incident card ────────────────────────────────────────────────────────────
function IncidentCard() {
  return (
    <div className="rounded-xl p-4 bg-bg-surface border border-border-base mb-6 mt-2">
      <div className="flex items-start gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold tracking-wider uppercase text-text-primary">P1 Outage</span>
            <span className="text-[11px] text-text-muted">02:17 UTC</span>
          </div>
          <p className="text-[13px] text-text-secondary leading-relaxed">
            S3 bucket <code className="text-[11px] font-mono bg-bg-raised border border-border-dim px-1 rounded text-text-primary">prod-uploads</code> public access
            enabled via Terraform override — 47K files exposed.
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Artifact chip ────────────────────────────────────────────────────────────
function ArtifactChip({
  artifact, show,
}: {
  artifact: typeof ARTIFACTS[number];
  show: boolean;
}) {
  const Icon = artifact.icon;

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 4 }}
          animate={{ opacity: 1, scale: 1,    y: 0 }}
          exit  ={{ opacity: 0, scale: 0.95,  y: -4 }}
          transition={{ duration: duration.standard, ease }}
          className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-bg-base border border-border-base"
        >
          <Icon className="w-3.5 h-3.5 flex-shrink-0 text-text-muted" />
          <span className="text-[13px] font-medium text-text-primary">{artifact.label}</span>
          <span className="ml-auto text-[10px] font-medium text-text-muted">✓ Ready</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ─── Interactive pipeline panel ───────────────────────────────────────────────
function PipelinePanel({ mouseX, mouseY }: { mouseX: number; mouseY: number }) {
  const [activeStage, setActiveStage] = useState(0);
  const [artifactsVisible, setArtifactsVisible] = useState<boolean[]>([false, false, false, false]);

  useEffect(() => {
    const cycle = () => {
      setActiveStage((prev) => {
        const next = (prev + 1) % (PIPELINE_STAGES.length + 1);

        if (next >= PIPELINE_STAGES.length) {
          setArtifactsVisible([true, true, true, true]);
          setTimeout(() => {
            setActiveStage(0);
            setArtifactsVisible([false, false, false, false]);
          }, 3500);
          return PIPELINE_STAGES.length;
        }

        if (next >= 4) {
          setArtifactsVisible((prev) => {
            const updated = [...prev];
            updated[next - 4] = true;
            return updated;
          });
        }
        return next;
      });
    };

    const timer = setInterval(cycle, 1500);
    return () => clearInterval(timer);
  }, []);

  // Subtle parallax translation
  const moveX = (mouseX - 0.5) * 8;
  const moveY = (mouseY - 0.5) * 8;

  return (
    <motion.div
      animate={{ x: moveX, y: moveY }}
      transition={{ type: 'spring', stiffness: 100, damping: 30 }}
      className="relative w-full max-w-sm mx-auto lg:mx-0"
    >
      <div className="relative bg-bg-base rounded-2xl p-6 border border-border-base shadow-sm">
        
        {/* Panel header */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] uppercase tracking-widest text-text-muted font-medium">Pipeline Status</span>
          <div className="flex items-center gap-1.5 bg-bg-surface px-2 py-0.5 rounded border border-border-dim">
            <span className="w-1.5 h-1.5 rounded-full bg-text-primary" />
            <span className="text-[10px] text-text-primary font-medium uppercase">Active</span>
          </div>
        </div>

        <IncidentCard />

        {/* Pipeline stages */}
        <div className="flex flex-col gap-3.5 mb-6 pl-1 relative z-10">
          {PIPELINE_STAGES.map((stage, i) => (
            <PipelineNode
              key={stage.id}
              stage={stage}
              index={i}
              activeStage={activeStage}
            />
          ))}
        </div>

        <div className="h-px bg-border-dim mb-4" />

        {/* Generated artifacts */}
        <div className="min-h-[140px]">
          <p className="text-[10px] uppercase tracking-widest text-text-muted mb-3 font-medium">
            Generated Artifacts
          </p>
          <div className="flex flex-col gap-2">
            {ARTIFACTS.map((artifact, i) => (
              <ArtifactChip
                key={artifact.label}
                artifact={artifact}
                show={artifactsVisible[i]}
              />
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Hero main component ──────────────────────────────────────────────────────
export function Hero() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 });

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    setMousePos({ x, y });
  }, []);

  return (
    <section
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className="relative min-h-screen flex items-center bg-bg-base overflow-hidden pt-16"
      aria-label="Hero section"
    >
      <div className="relative z-10 w-full max-w-7xl mx-auto px-6 lg:px-12 py-16 lg:py-24">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-24 items-center">

          {/* ── LEFT — Copy ── */}
          <div className="flex flex-col max-w-[640px]">
            
            {/* Eyebrow */}
            <motion.div
              initial={fadeUp.initial}
              animate={fadeUp.animate}
              transition={{ ...fadeUp.transition, delay: 0 }}
              className="mb-8"
            >
              <span className="inline-flex items-center px-2.5 py-1 rounded-full border border-border-strong text-[11px] font-mono tracking-wide text-text-secondary uppercase" role="status" aria-live="polite">
                AI-Powered Reliability
              </span>
            </motion.div>

            {/* Headline */}
            <div className="flex flex-col mb-6">
              <motion.h1 
                initial={fadeUp.initial}
                animate={fadeUp.animate}
                transition={{ ...fadeUp.transition, delay: 0.08 }}
                className="text-3xl sm:text-4xl lg:text-[64px] font-medium leading-[1.1] sm:leading-[1.05] tracking-[-0.04em] text-text-primary"
              >
                Turn cloud <br className="hidden sm:block" />
                <motion.span
                  initial={{ clipPath: 'inset(0 100% 0 0)' }}
                  animate={{ clipPath: 'inset(0 0% 0 0)' }}
                  transition={{ duration: 0.8, ease, delay: 0.4 }}
                  className="inline-block text-text-muted italic pr-2"
                >
                  incidents
                </motion.span>
                <br className="hidden sm:block" />
                into prevention.
              </motion.h1>
            </div>

            {/* Subheadline */}
            <motion.p
              initial={fadeUp.initial}
              animate={fadeUp.animate}
              transition={{ ...fadeUp.transition, delay: 0.16 }}
              className="text-lg text-text-secondary leading-relaxed mb-10 max-w-md"
            >
              Upload an incident report and generate enforceable guardrails, alerts,
              runbooks, and infrastructure patches in minutes — not weeks.
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={fadeUp.initial}
              animate={fadeUp.animate}
              transition={{ ...fadeUp.transition, delay: 0.22 }}
              className="flex items-center gap-4 flex-wrap mb-12"
            >
              <Link href="/incidents/new" className="inline-block">
                <motion.button
                  whileHover={{ y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  transition={spring.tactile}
                  className="inline-flex items-center justify-center gap-2 h-11 px-6 rounded-lg bg-inverse-bg text-inverse-text font-medium text-[15px] transition-opacity hover:opacity-90"
                >
                  Analyze an incident
                  <ArrowRight className="w-4 h-4 ml-1 opacity-80" />
                </motion.button>
              </Link>
              <Link href="/workflow" className="inline-block">
                <motion.button
                  whileHover={{ y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  transition={spring.tactile}
                  className="inline-flex items-center justify-center gap-2 h-11 px-6 rounded-lg bg-transparent text-text-primary font-medium text-[15px] border border-border-strong hover:bg-bg-surface transition-colors"
                >
                  <Play className="w-4 h-4 mr-1 opacity-80" />
                  View live workflow
                </motion.button>
              </Link>
            </motion.div>

            {/* Stat chips */}
            <StaggerGroup 
              initialDelay={0.3} 
              delayStep={0.06}
              className="flex items-center gap-x-4 sm:gap-x-6 gap-y-4 flex-wrap pt-6 border-t border-border-dim"
            >
              {STAT_CHIPS.map((chip) => {
                const Icon = chip.icon;
                return (
                  <div key={chip.label} className="flex flex-col gap-1">
                    <div className="flex items-center gap-1.5 text-text-primary">
                      <Icon className="w-3.5 h-3.5 text-text-muted" />
                      <span className="text-sm font-semibold">{chip.label}</span>
                    </div>
                    <span className="text-[11px] text-text-muted uppercase tracking-wider">{chip.sub}</span>
                  </div>
                );
              })}
            </StaggerGroup>
          </div>

          {/* ── RIGHT — Interactive Pipeline Panel ── */}
          <Reveal delay={0.3} className="block lg:block">
            <PipelinePanel mouseX={mousePos.x} mouseY={mousePos.y} />
          </Reveal>
        </div>
      </div>
    </section>
  );
}
