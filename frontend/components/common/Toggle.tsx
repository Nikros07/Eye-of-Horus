"use client";

import { motion } from "framer-motion";
import clsx from "clsx";

export default function Toggle({
  checked,
  onChange,
  disabled,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={clsx(
        "relative h-[26px] w-[46px] shrink-0 rounded-full transition-colors duration-200 disabled:opacity-40",
        checked ? "bg-gold" : "bg-white/[0.12]"
      )}
    >
      <motion.span
        layout
        transition={{ type: "spring", stiffness: 500, damping: 32 }}
        className="absolute top-[3px] h-5 w-5 rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.4)]"
        style={{ left: checked ? 23 : 3 }}
      />
    </button>
  );
}
