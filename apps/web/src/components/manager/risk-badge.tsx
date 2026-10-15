import { cn } from "@/lib/utils";
import type { RiskType } from "@/lib/api/types";

const LABEL: Record<RiskType, string> = {
  stockout_risk: "Stockout risk",
  overstock: "Overstock",
  reorder: "Reorder",
  unmet_spike: "Unmet spike",
};

const STYLE: Record<RiskType, string> = {
  stockout_risk: "bg-error-container/50 text-error",
  overstock: "bg-surface-container-high text-primary",
  reorder: "bg-secondary-fixed text-on-secondary-fixed-variant",
  unmet_spike: "bg-tertiary-fixed text-tertiary",
};

export function RiskBadge({
  risk,
  className,
}: {
  risk: RiskType;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 font-label-mono text-caption whitespace-nowrap",
        STYLE[risk],
        className,
      )}
    >
      {LABEL[risk]}
    </span>
  );
}

export { LABEL as riskLabel };
