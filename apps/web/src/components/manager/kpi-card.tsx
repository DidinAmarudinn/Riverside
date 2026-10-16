import { cn } from "@/lib/utils";

/** White card: round icon chip and label, one big light-weight number, one caption. `lime` marks the one card that matters. */
export function KpiCard({
  label,
  value,
  suffix,
  footerLabel,
  footerValue,
  tone = "neutral",
  icon: Icon,
  loading = false,
}: {
  label: string;
  value: string;
  suffix?: string;
  footerLabel?: string;
  footerValue?: string;
  tone?: "neutral" | "error" | "primary" | "warning" | "lime";
  icon: React.ComponentType<{ className?: string }>;
  /** Data still on its way: keep the card, pulse where the number goes. */
  loading?: boolean;
}) {
  const lime = tone === "lime";
  const caption = [footerValue, footerLabel].filter(Boolean).join(" · ");
  return (
    <div className={cn("flex flex-col gap-2.5 rounded-xl p-5", lime ? "bg-primary-fixed" : "bg-surface-container-lowest")}>
      <div className="flex items-center gap-2.5 text-body-default text-on-surface">
        <span className={cn("flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full", lime ? "bg-white" : "bg-surface-container-low")}>
          <Icon className="h-[17px] w-[17px] text-on-surface" aria-hidden />
        </span>
        {label}
      </div>
      {loading ? (
        <>
          <span className="h-10 w-24 animate-pulse rounded-md bg-surface-container-low" aria-hidden />
          <span className="h-4 w-3/4 animate-pulse rounded bg-surface-container-low" aria-hidden />
        </>
      ) : (
      <>
      <div className="flex items-baseline gap-2">
        <span className="text-kpi-stat tabular-nums text-on-surface">{value}</span>
        {suffix ? <span className="text-caption text-on-surface-variant">{suffix}</span> : null}
      </div>
      {caption ? <span className={cn("text-caption", lime ? "text-on-surface" : "text-on-surface-variant")}>{caption}</span> : null}
      </>
      )}
    </div>
  );
}
