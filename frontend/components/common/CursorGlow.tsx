"use client";

import { useEffect, useState } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";

const INTERACTIVE_SELECTOR = 'a, button, [role="button"], input, select, .cursor-interactive';

/**
 * A soft light that follows the cursor across the whole app — purely
 * decorative, pointer-events-none, and never hides the native cursor (this
 * is a data-dense trading terminal; precise clicking matters more than a
 * novelty cursor replacement). It brightens and tightens over interactive
 * elements so hovering a button/link/card has a tactile "magnetic" feel.
 */
export default function CursorGlow() {
  const x = useMotionValue(-400);
  const y = useMotionValue(-400);
  const springX = useSpring(x, { damping: 28, stiffness: 180, mass: 0.5 });
  const springY = useSpring(y, { damping: 28, stiffness: 180, mass: 0.5 });
  const [hovering, setHovering] = useState(false);

  useEffect(() => {
    function handleMove(e: MouseEvent) {
      x.set(e.clientX);
      y.set(e.clientY);
      const target = e.target as HTMLElement;
      setHovering(Boolean(target?.closest?.(INTERACTIVE_SELECTOR)));
    }
    window.addEventListener("mousemove", handleMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMove);
  }, [x, y]);

  return (
    <>
      <motion.div
        aria-hidden
        className="pointer-events-none fixed left-0 top-0 z-[60] rounded-full mix-blend-screen"
        animate={{
          width: hovering ? 320 : 480,
          height: hovering ? 320 : 480,
          opacity: hovering ? 0.9 : 0.55,
        }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        style={{
          x: springX,
          y: springY,
          translateX: "-50%",
          translateY: "-50%",
          background: hovering
            ? "radial-gradient(circle, rgba(216,179,108,0.16) 0%, rgba(216,179,108,0.05) 45%, transparent 72%)"
            : "radial-gradient(circle, rgba(216,179,108,0.08) 0%, rgba(91,141,239,0.03) 45%, transparent 70%)",
        }}
      />
      <motion.div
        aria-hidden
        className="pointer-events-none fixed left-0 top-0 z-[60] rounded-full border border-gold/40"
        animate={{
          width: hovering ? 34 : 16,
          height: hovering ? 34 : 16,
          opacity: hovering ? 0.9 : 0.4,
        }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        style={{
          x: springX,
          y: springY,
          translateX: "-50%",
          translateY: "-50%",
        }}
      />
    </>
  );
}
