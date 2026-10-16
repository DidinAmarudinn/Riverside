import type { RiskType } from "@/lib/api/types";
import { StatusTag, type StatusTone } from "@/components/ui/status-tag";

const LABEL: Record<RiskType, string> = {
  stockout_risk: "Stockout risk",
  overstock: "Overstock",
  reorder: "Reorder",
  unmet_spike: "Unmet spike",
};

const TONE: Record<RiskType, StatusTone> = {
  stockout_risk: "red",
  overstock: "grey",
  reorder: "amber",
  unmet_spike: "lime",
};

export function RiskBadge({ risk, className }: { risk: RiskType; className?: string }) {
  return (
    <StatusTag tone={TONE[risk]} className={className}>
      {LABEL[risk]}
    </StatusTag>
  );
}

export { LABEL as riskLabel };
