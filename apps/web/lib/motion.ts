import type { Transition, Variants } from "framer-motion";

export const spring: Transition = { type: "spring", stiffness: 320, damping: 30, mass: .8 };
export const swift: Transition = { duration: .2, ease: [.22, 1, .36, 1] };
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 8, filter: "blur(4px)" },
  enter: { opacity: 1, y: 0, filter: "blur(0px)", transition: { ...swift, staggerChildren: .035 } },
  exit: { opacity: 0, y: -5, transition: { duration: .12 } }
};
export const staggerItem: Variants = {
  initial: { opacity: 0, y: 8 },
  enter: { opacity: 1, y: 0, transition: spring }
};
