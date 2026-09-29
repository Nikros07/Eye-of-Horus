"use client";

import { useEffect, useRef } from "react";
import { useMotionValue, useSpring, useInView } from "framer-motion";

interface AnimatedNumberProps {
  value: number;
  format?: (n: number) => string;
  className?: string;
}

export default function AnimatedNumber({ value, format, className }: AnimatedNumberProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 90, damping: 24, mass: 0.9 });

  useEffect(() => {
    if (inView) motionValue.set(value);
  }, [inView, value, motionValue]);

  useEffect(() => {
    return spring.on("change", (v) => {
      if (ref.current) ref.current.textContent = format ? format(v) : v.toFixed(2);
    });
  }, [spring, format]);

  return (
    <span ref={ref} className={className}>
      {format ? format(0) : "0.00"}
    </span>
  );
}
