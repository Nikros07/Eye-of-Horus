export default function DemoDataBadge({ className }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border border-white/10 bg-white/[0.04] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-text-tertiary ${className || ""}`}
    >
      Demo
    </span>
  );
}
