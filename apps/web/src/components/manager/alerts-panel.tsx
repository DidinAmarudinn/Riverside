import type { AlertItem } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const dotTone: Record<AlertItem["type"], string> = {
  stockout_risk: "bg-status-red",
  unmet_spike: "bg-primary-fixed",
  overstock: "bg-outline",
  reorder: "bg-status-amber",
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
            "flex items-start gap-2.5 rounded-xl bg-surface-container-low p-3 transition-colors",
            highlightId === alert.id &&
              "bg-secondary-fixed ring-2 ring-primary-fixed",
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
