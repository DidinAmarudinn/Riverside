import type { AlertItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const dotTone: Record<AlertItem["type"], string> = {
  stockout_risk: "bg-error",
  unmet_spike: "bg-tertiary",
  overstock: "bg-surface-container-high",
  reorder: "bg-secondary-container",
};

export function AlertsPanel({
  alerts,
  highlightId,
}: {
  alerts: AlertItem[];
  highlightId?: string | null;
}) {
  return (
    <div className="flex flex-col gap-2">
      {alerts.slice(0, 20).map((alert) => (
        <div
          key={alert.id}
          className={cn(
            "flex items-start gap-2.5 rounded-lg bg-surface-container-low/40 p-2.5 transition-colors",
            highlightId === alert.id &&
              "ring-2 ring-primary/40 animate-pulse",
          )}
        >
          <span
            className={cn(
              "mt-1 h-2.5 w-2.5 flex-shrink-0 rounded-full",
              dotTone[alert.type],
            )}
          />
          <div className="flex flex-col">
            <span className="text-body-medium text-on-surface">
              {alert.title}
            </span>
            <span className="mt-0.5 text-caption text-on-surface-variant">
              {alert.body}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
