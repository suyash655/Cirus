// src/lib/motion/tokens.ts
export const ease = [0.22, 1, 0.36, 1] as const; // primary ease-out

export const duration = {
  fast: 0.18,     // 150–200ms — micro interactions
  standard: 0.4,  // 350–500ms — component transitions
  section: 0.6,   // 500–700ms — section reveals
  complex: 0.9,   // 700–1000ms max — layered/product sequences
};

export const spring = {
  tactile: { type: 'spring', stiffness: 300, damping: 30, mass: 1 }, // buttons
  card:    { type: 'spring', stiffness: 220, damping: 26 },          // hover lift
};

export const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: duration.section, ease },
};

export const stagger = (i: number, step = 0.06) => ({
  transition: { delay: i * step, duration: duration.standard, ease },
});
