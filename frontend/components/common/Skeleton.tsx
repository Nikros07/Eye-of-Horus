import clsx from "clsx";

/** A shimmering placeholder block. Use in place of real content while an
 * SWR request is still in flight, so a page never flashes a "nothing here"
 * empty state before it actually knows whether there is anything there. */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={clsx("skeleton rounded-md", className)} />;
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={clsx("rounded-2xl border border-border glass p-5", className)}>
      <Skeleton className="h-3 w-20" />
      <Skeleton className="mt-3 h-6 w-28" />
      <Skeleton className="mt-4 h-3 w-full" />
      <Skeleton className="mt-2 h-3 w-2/3" />
    </div>
  );
}

/** A single `<tr>` of shimmering cells, for tables that use their own
 * <table>/<tbody> shell (pass matching `cols`). */
export function SkeletonRow({ cols = 4 }: { cols?: number }) {
  return (
    <tr className="border-t border-border first:border-t-0">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3.5">
          <Skeleton className="h-3.5 w-full max-w-[120px]" />
        </td>
      ))}
    </tr>
  );
}
