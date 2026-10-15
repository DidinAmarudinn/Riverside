import { cn } from "@/lib/utils";

export function KpiCard({
  label,
  value,
  suffix,
  footerLabel,
  footerValue,
  tone = "neutral",
  icon: Icon,
}: {
  label: string;
  value: string;
  suffix?: string;
  footerLabel: string;
  footerValue: string;
  tone?: "neutral" | "error" | "primary" | "warning";
  icon: React.ComponentType<{ className?: string }>;
}) {
  const valueTone =
    tone === "error"
      ? "text-error"
      : tone === "primary"
        ? "text-on-surface"
        : "text-on-surface";
  const iconTone =
    tone === "error"
      ? "bg-error-container/40 text-error"
      : tone === "warning"
        ? "bg-secondary-container/30 text-secondary"
        : "bg-surface-container-high text-primary";
  const footerTone =
    tone === "error"
      ? "text-error"
      : tone === "primary"
        ? "text-primary"
        : "text-secondary";

  return (
    <div className="flex flex-col justify-between rounded-xl bg-surface-container-lowest p-6 shadow-sm">
      <div>
        <div className="mb-1 flex items-center justify-between">
          <span className="font-microcopy-caps text-microcopy-caps uppercase text-on-surface-variant">
            {label}
          </span>
          <div
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-lg",
              iconTone,
            )}
          >
            <Icon className="h-[18px] w-[18px]" aria-hidden />
          </div>
        </div>
        <div className="mt-1 flex items-baseline gap-2">
          <span
            className={cn(
              "text-kpi-stat tabular-nums tracking-tight",
              valueTone,
            )}
          >
            {value}
          </span>
          {suffix ? (
            <span className="text-caption text-on-surface-variant">
              {suffix}
            </span>
          ) : null}
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-surface-container pt-3">
        <span className={cn("font-label-mono text-caption", footerTone)}>
          {footerValue}
        </span>
        <span className="text-caption text-on-surface-variant">
          {footerLabel}
        </span>
      </div>
    </div>
  );
}
