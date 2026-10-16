import { cn } from "@/lib/utils";
import { RiverMark } from "./river-mark";

export function BrandMark({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <RiverMark className="h-10 w-10" />
      <div className="flex flex-col">
        <span className="text-[19px] font-semibold leading-tight tracking-[-0.03em] text-on-surface">
          Demand Radar
        </span>
        <span className="text-caption leading-none text-on-surface-variant">
          by Team Riverside
        </span>
      </div>
    </div>
  );
}
