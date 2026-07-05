"use client";

import * as React from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";

export function AnimatedCounter({
  value,
  formatter = (number) => String(Math.round(number))
}: {
  value: number;
  formatter?: (value: number) => string;
}) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { mass: 0.8, stiffness: 90, damping: 18 });
  const display = useTransform(spring, (latest) => formatter(latest));

  React.useEffect(() => {
    motionValue.set(value);
  }, [motionValue, value]);

  return <motion.span>{display}</motion.span>;
}

