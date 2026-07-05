"use client";

import { motion, useReducedMotion } from "framer-motion";
import { usePathname } from "next/navigation";
import { pageVariants } from "@/lib/motion";

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const reduced = useReducedMotion();
  return <motion.div key={pathname} variants={reduced ? undefined : pageVariants} initial="initial" animate="enter" exit="exit">{children}</motion.div>;
}
