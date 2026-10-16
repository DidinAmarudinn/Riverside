import { cn } from "@/lib/utils";

const TONE = {
  red: "bg-status-red-bg text-status-red",
  amber: "bg-status-amber-bg text-status-amber",
  green: "bg-status-green-bg text-status-green",
  grey: "bg-surface-container-low text-on-surface-variant",
  lime: "bg-primary-fixed text-on-primary-fixed",
} as const;

export type StatusTone = keyof typeof TONE;

/** A small pill with a dot: the site's one way to show state (out of stock, reorder, live, …). */
export function StatusTag({ tone, children, className }: { tone: StatusTone; children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-caption font-semibold", TONE[tone], className)}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}
