'use client';

import React from 'react';
import { motion, HTMLMotionProps, useSpring, useMotionTemplate, useMotionValue, useReducedMotion } from 'framer-motion';
import { fadeUp, duration, ease } from '@/lib/motion/tokens';
import { cn } from '@/lib/utils';

// Hook to get reduced motion preference
const useReducedMotionValue = () => {
  const prefersReducedMotion = useReducedMotion();
  return prefersReducedMotion;
};

interface RevealProps extends HTMLMotionProps<'div'> {
  delay?: number;
}

export function Reveal({ children, className, delay = 0, ...props }: RevealProps) {
  const prefersReducedMotion = useReducedMotionValue();
  
  return (
    <motion.div
      initial={prefersReducedMotion ? { opacity: 0 } : fadeUp.initial}
      whileInView={prefersReducedMotion ? { opacity: 1 } : fadeUp.animate}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ 
        ...fadeUp.transition, 
        delay: prefersReducedMotion ? 0 : delay,
        duration: prefersReducedMotion ? 0.01 : fadeUp.transition.duration
      }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}

interface StaggerGroupProps {
  delayStep?: number;
  initialDelay?: number;
  className?: string;
  children?: React.ReactNode;
}

export function StaggerGroup({ 
  children, 
  className, 
  delayStep = 0.06, 
  initialDelay = 0,
}: StaggerGroupProps) {
  const prefersReducedMotion = useReducedMotionValue();
  
  return (
    <div className={className}>
      {React.Children.map(children, (child, i) => {
        if (!React.isValidElement(child)) return child;
        return (
          <motion.div
            initial={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: 16 }}
            whileInView={prefersReducedMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ 
              delay: prefersReducedMotion ? 0 : initialDelay + i * delayStep, 
              duration: prefersReducedMotion ? 0.01 : duration.standard, 
              ease: prefersReducedMotion ? 'linear' : ease 
            }}
          >
            {child}
          </motion.div>
        );
      })}
    </div>
  );
}

interface HoverCardProps {
  accentColor?: string;
  className?: string;
  children?: React.ReactNode;
}

export function HoverCard({ children, className, accentColor = 'hsl(var(--cyan))' }: HoverCardProps) {
  const prefersReducedMotion = useReducedMotionValue();
  
  return (
    <motion.div
      whileHover={prefersReducedMotion ? {} : { y: -2 }}
      transition={{ duration: prefersReducedMotion ? 0 : duration.fast, ease: prefersReducedMotion ? 'linear' : ease }}
      className={cn(
        'group relative rounded-xl p-6 border border-border-base bg-surface transition-colors duration-200',
        'hover:border-border-strong hover:shadow-elevation-1',
        className
      )}
    >
      {children}
    </motion.div>
  );
}

// New: Magnetic hover effect for buttons and interactive elements
interface MagneticButtonProps {
  strength?: number;
  className?: string;
  children?: React.ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
}

export function MagneticButton({ children, strength = 20, className, onClick, type = 'button' }: MagneticButtonProps) {
  const ref = React.useRef<HTMLButtonElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const prefersReducedMotion = useReducedMotionValue();
  
  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (prefersReducedMotion || !ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const mouseX = e.clientX - centerX;
    const mouseY = e.clientY - centerY;
    
    x.set(mouseX / strength);
    y.set(mouseY / strength);
  };
  
  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };
  
  return (
    <motion.button
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ x, y }}
      transition={{ type: 'spring', stiffness: prefersReducedMotion ? 0 : 150, damping: prefersReducedMotion ? 0 : 15 }}
      className={className}
      onClick={onClick}
      type={type}
    >
      {children}
    </motion.button>
  );
}

// New: Spotlight hover effect for cards
interface SpotlightCardProps {
  spotlightColor?: string;
  className?: string;
  children?: React.ReactNode;
}

export function SpotlightCard({ children, className, spotlightColor = 'hsl(var(--cyan))' }: SpotlightCardProps) {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const prefersReducedMotion = useReducedMotionValue();
  const spotlightX = useSpring(mouseX, { stiffness: prefersReducedMotion ? 0 : 300, damping: prefersReducedMotion ? 0 : 30 });
  const spotlightY = useSpring(mouseY, { stiffness: prefersReducedMotion ? 0 : 300, damping: prefersReducedMotion ? 0 : 30 });
  
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (prefersReducedMotion) return;
    const rect = e.currentTarget.getBoundingClientRect();
    mouseX.set(e.clientX - rect.left);
    mouseY.set(e.clientY - rect.top);
  };
  
  const background = useMotionTemplate`radial-gradient(circle at ${spotlightX}px ${spotlightY}px, ${spotlightColor} 0%, transparent 80%)`;
  
  return (
    <motion.div
      onMouseMove={handleMouseMove}
      whileHover={prefersReducedMotion ? {} : { y: -2 }}
      transition={{ duration: prefersReducedMotion ? 0 : duration.fast, ease: prefersReducedMotion ? 'linear' : ease }}
      className={cn('relative overflow-hidden rounded-xl group border border-border-base hover:border-border-strong transition-colors duration-200', className)}
    >
      <motion.div
        className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 pointer-events-none"
        style={{ background }}
      />
      {children}
    </motion.div>
  );
}

// New: Fade in scale animation for modal-like content
interface FadeInScaleProps {
  delay?: number;
  className?: string;
  children?: React.ReactNode;
}

export function FadeInScale({ children, className, delay = 0 }: FadeInScaleProps) {
  const prefersReducedMotion = useReducedMotionValue();
  
  return (
    <motion.div
      initial={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: prefersReducedMotion ? 1 : 1 }}
      exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
      transition={{ duration: prefersReducedMotion ? 0.01 : duration.standard, ease: prefersReducedMotion ? 'linear' : ease, delay: prefersReducedMotion ? 0 : delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// New: Slide in from specific direction
interface SlideInProps {
  direction?: 'left' | 'right' | 'up' | 'down';
  delay?: number;
  className?: string;
  children?: React.ReactNode;
}

export function SlideIn({ children, className, direction = 'up', delay = 0 }: SlideInProps) {
  const prefersReducedMotion = useReducedMotionValue();
  
  const variants = {
    left: prefersReducedMotion ? { opacity: 0 } : { x: -50, opacity: 0 },
    right: prefersReducedMotion ? { opacity: 0 } : { x: 50, opacity: 0 },
    up: prefersReducedMotion ? { opacity: 0 } : { y: 50, opacity: 0 },
    down: prefersReducedMotion ? { opacity: 0 } : { y: -50, opacity: 0 },
  };
  
  return (
    <motion.div
      initial={variants[direction]}
      whileInView={prefersReducedMotion ? { opacity: 1 } : { x: 0, y: 0, opacity: 1 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: prefersReducedMotion ? 0.01 : duration.standard, ease: prefersReducedMotion ? 'linear' : ease, delay: prefersReducedMotion ? 0 : delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
