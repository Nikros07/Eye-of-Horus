"use client";

import { useRef, MouseEvent, ReactNode } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import clsx from "clsx";

interface Card3DProps {
  children: ReactNode;
  className?: string;
  glow?: "gold" | "danger" | "info" | "signal" | "none";
  intensity?: number; // max tilt in degrees
  onClick?: () => void;
}

const glowColor: Record<string, string> = {
  gold: "rgba(216,179,108,0.16)",
  danger: "rgba(229,85,92,0.16)",
  info: "rgba(91,141,239,0.16)",
  signal: "rgba(139,127,232,0.16)",
  none: "rgba(255,255,255,0.08)",
};

export default function Card3D({ children, className, glow = "gold", intensity = 8, onClick }: Card3DProps) {
  const ref = useRef<HTMLDivElement>(null);

  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);

  const springConfig = { stiffness: 220, damping: 22, mass: 0.6 };
  const rotateX = useSpring(useTransform(py, [0, 1], [intensity, -intensity]), springConfig);
  const rotateY = useSpring(useTransform(px, [0, 1], [-intensity, intensity]), springConfig);
  const lightX = useSpring(useTransform(px, [0, 1], [0, 100]), springConfig);
  const lightY = useSpring(useTransform(py, [0, 1], [0, 100]), springConfig);
  const scale = useSpring(1, springConfig);

  function handleMove(e: MouseEvent<HTMLDivElement>) {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    px.set((e.clientX - rect.left) / rect.width);
    py.set((e.clientY - rect.top) / rect.height);
  }

  function handleEnter() {
    scale.set(1.015);
  }

  function handleLeave() {
    px.set(0.5);
    py.set(0.5);
    scale.set(1);
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMove}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      onClick={onClick}
      style={{
        rotateX,
        rotateY,
        scale,
        transformStyle: "preserve-3d",
        transformPerspective: 900,
      }}
      className={clsx(
        "group relative rounded-2xl border border-border glass shadow-card transition-shadow duration-300",
        "hover:shadow-card-hover",
        onClick && "cursor-pointer",
        className
      )}
    >
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: useTransform(
            [lightX, lightY],
            ([x, y]: number[]) => `radial-gradient(320px circle at ${x}% ${y}%, ${glowColor[glow]}, transparent 70%)`
          ),
        }}
      />
      <div aria-hidden className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-white/[0.04]" />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
      >
        <div className="absolute -inset-y-full left-[-60%] w-[40%] -rotate-12 bg-gradient-to-r from-transparent via-white/[0.06] to-transparent transition-transform duration-[1100ms] ease-out group-hover:translate-x-[300%]" />
      </div>
      <div style={{ transform: "translateZ(24px)" }} className="relative">
        {children}
      </div>
    </motion.div>
  );
}
