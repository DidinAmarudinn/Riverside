import { cn } from "@/lib/utils";
import type { Outcome } from "@/lib/api/types";

const STYLE: Record<Outcome, string> = {
  purchased: "bg-primary-fixed text-on-primary-fixed",
  out_of_stock: "bg-error-container/50 text-error",
  not_carried: "bg-tertiary-fixed text-tertiary",
  substituted: "bg-surface-container-high text-primary",
};

export function OutcomePill({
  outcome,
  className,
}: {
  outcome: Outcome;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "rounded px-2 py-0.5 font-label-mono text-[11px]",
        STYLE[outcome],
        className,
      )}
    >
      {outcome}
    </span>
  );
}
