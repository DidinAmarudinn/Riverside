import { Radar } from "lucide-react";
import { cn } from "@/lib/utils";

export function BrandMark({
  compact = false,
  className,
}: {
  compact?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-container-low text-primary-container">
        <Radar className="h-[22px] w-[22px]" aria-hidden />
      </div>
      {!compact ? (
        <div className="flex flex-col">
          <span className="text-headline-sm leading-none tracking-tight text-on-surface">
            Demand Radar
          </span>
          <span className="mt-1 font-label-mono text-caption leading-none text-on-surface-variant">
            Retail Intelligence
          </span>
        </div>
      ) : null}
    </div>
  );
}
