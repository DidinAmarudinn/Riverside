import { StatusTag, type StatusTone } from "@/components/ui/status-tag";
import type { Outcome } from "@/lib/api/types";

const LABEL: Record<Outcome, string> = {
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
      {LABEL[outcome] ?? outcome}
    </StatusTag>
  );
}
