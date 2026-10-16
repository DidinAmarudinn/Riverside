"use client";

import type { EvidenceItem } from "@/lib/api/types";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { formatDateTimeWib } from "@/lib/format";
import { OutcomePill } from "@/components/manager/outcome-pill";


export function EvidenceDrawer({
  open,
  onOpenChange,
  skuName,
  total,
  items,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  skuName: string;
  total: number;
  items: EvidenceItem[];
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-lg">
        <SheetHeader>
          <div className="flex items-center gap-2">
            <SheetTitle>Evidence</SheetTitle>
            <span className="rounded-full bg-surface-container-low px-2.5 py-1 text-caption text-on-surface-variant">
              {total} conversations
            </span>
          </div>
          <SheetDescription>
            What shoppers typed at the kiosk about {skuName}. Simulated conversations.
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-2 overflow-y-auto px-6 pb-6">
          {items.map((item) => (
            <div
              key={item.id}
              className={cn(
                "flex flex-col gap-1.5 rounded-xl bg-surface-container-low p-3.5",
                item.highlight && "ring-2 ring-primary/50",
              )}
            >
              <div className="flex items-center justify-between text-caption">
                <span className="text-caption text-on-surface-variant">
                  {formatDateTimeWib(item.ts)} • {item.channel}
                </span>
                <OutcomePill outcome={item.outcome} />
              </div>
              <div className="text-body-default italic text-on-surface">
                “{item.text}”
              </div>
              <div className="flex items-center justify-between text-caption text-on-surface-variant">
                <span className="truncate">Matched: {item.matchedName}</span>
                <span className="font-medium text-primary-container">
                  {Math.round(item.confidence * 100)}% confidence
                </span>
              </div>
              {item.intent ? (
                <span className="text-[11px] text-outline">
                  Intent: {item.intent}
                </span>
              ) : null}
            </div>
          ))}
        </div>

        <div className="mt-auto flex items-center justify-between border-t border-outline-variant px-6 py-3 text-caption text-on-surface-variant">
          <span className="flex items-center gap-1">
            Read from informal Indonesian by the signal extractor
          </span>
          <span>
            Showing {items.length} of {total}
          </span>
        </div>
      </SheetContent>
    </Sheet>
  );
}
