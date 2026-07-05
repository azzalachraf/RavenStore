import type { Transition, Variants } from "framer-motion";

export const spring: Transition = { type: "spring", stiffness: 300, damping: 28, mass: .82 };
export const swift: Transition = { duration: .22, ease: [.22, 1, .36, 1] };
export const pageVariants: Variants = {
  initial: { opacity: 0, y: 8, filter: "blur(4px)" },
  enter: { opacity: 1, y: 0, filter: "blur(0px)", transition: swift },
  exit: { opacity: 0, y: -5, transition: { duration: .12 } }
};
