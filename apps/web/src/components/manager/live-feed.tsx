import { CornerDownRight, HelpCircle, ArrowLeftRight } from "lucide-react";
import type { LiveSignal } from "@/lib/api/types";
import { formatTimeWib } from "@/lib/format";
import { OutcomePill } from "./outcome-pill";

function MatchLine({ signal }: { signal: LiveSignal }) {
  if (signal.outcome === "not_carried") {
    return (
      <div className="flex items-center gap-1 text-caption text-on-surface-variant">
        <HelpCircle className="h-[14px] w-[14px]" aria-hidden />
        <span>Unregistered import query</span>
      </div>
    );
  }
  if (signal.outcome === "substituted") {
    return (
      <div className="flex items-center gap-1 text-caption text-primary">
        <ArrowLeftRight className="h-[14px] w-[14px]" aria-hidden />
        <span>Substituted with: {signal.substituteName ?? signal.matchedName}</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1 text-caption text-primary">
      <CornerDownRight className="h-[14px] w-[14px]" aria-hidden />
      <span>Matched: {signal.matchedName ?? "—"}</span>
    </div>
  );
}

export function LiveFeed({ signals }: { signals: LiveSignal[] }) {
  return (
    <div className="flex flex-col gap-2">
      {signals.slice(0, 30).map((signal) => (
        <div
          key={signal.id}
          className="flex flex-col gap-1 rounded-lg bg-surface-container-low/70 p-2.5"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-label-mono text-caption text-on-surface-variant">
              {formatTimeWib(signal.ts)} WIB • {signal.source ?? "Kiosk"}
            </span>
            <OutcomePill outcome={signal.outcome} />
          </div>
          <p className="text-body-default italic text-on-surface">
            “{signal.requestedText}”
          </p>
          <MatchLine signal={signal} />
        </div>
      ))}
    </div>
  );
}
