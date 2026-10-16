import { StatusTag, type StatusTone } from "@/components/ui/status-tag";
import type { Outcome } from "@/lib/api/types";

export const OUTCOME_LABEL: Record<Outcome, string> = {
  purchased: "Purchased",
  out_of_stock: "Out of stock",
  not_carried: "Not carried",
  substituted: "Substituted",
};

const TONE: Record<Outcome, StatusTone> = {
  purchased: "green",
  out_of_stock: "red",
  not_carried: "grey",
  substituted: "amber",
};

export function OutcomePill({
  outcome,
  className,
}: {
  outcome: Outcome;
  className?: string;
}) {
  return (
    <StatusTag tone={TONE[outcome] ?? "grey"} className={className}>
      {OUTCOME_LABEL[outcome] ?? outcome}
    </StatusTag>
  );
}
