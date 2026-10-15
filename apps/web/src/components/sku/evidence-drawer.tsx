"use client";

import { useMemo, useState } from "react";
import { AudioLines } from "lucide-react";
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

const FILTERS = ["All", "Voice Kiosks", "Search Bar"] as const;
type Filter = (typeof FILTERS)[number];

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
  const [filter, setFilter] = useState<Filter>("All");

  const filtered = useMemo(() => {
    if (filter === "All") return items;
    const needle = filter === "Voice Kiosks" ? "voice" : "search";
    return items.filter((i) => i.channel.toLowerCase().includes(needle));
  }, [filter, items]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-lg">
        <SheetHeader>
          <div className="flex items-center gap-2">
            <SheetTitle>Evidence</SheetTitle>
            <span className="rounded-full bg-secondary-container px-2 py-0.5 font-label-mono text-[11px] font-bold text-on-secondary-fixed">
              {total} conversations
            </span>
          </div>
          <SheetDescription>
            Direct conversational logs &amp; touchpoint transcripts for {skuName}
          </SheetDescription>
        </SheetHeader>

        <div className="flex items-center gap-1.5 overflow-x-auto px-6">
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={cn(
                "whitespace-nowrap rounded-full px-2.5 py-1 text-[12px] font-medium transition",
                filter === f
                  ? "bg-primary-container text-on-primary"
                  : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container",
              )}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-2 overflow-y-auto px-6 pb-6">
          {filtered.map((item) => (
            <div
              key={item.id}
              className={cn(
                "flex flex-col gap-1.5 rounded-lg bg-surface-container-low p-3",
                item.highlight && "ring-2 ring-primary/50",
              )}
            >
              <div className="flex items-center justify-between text-caption">
                <span className="font-label-mono text-[11px] text-on-surface-variant">
                  {formatDateTimeWib(item.ts)} • {item.channel}
                </span>
                <OutcomePill outcome={item.outcome} />
              </div>
              <div className="rounded-lg bg-surface-container-lowest px-2.5 py-2 text-body-medium italic text-on-surface">
                “{item.text}”
              </div>
              <div className="flex items-center justify-between text-caption text-on-surface-variant">
                <span className="truncate">Matched: {item.matchedName}</span>
                <span className="font-label-mono font-medium text-primary-container">
                  {Math.round(item.confidence * 100)}% conf.
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

        <div className="mt-auto flex items-center justify-between border-t border-surface-container px-6 py-3 font-label-mono text-[11px] text-on-surface-variant">
          <span className="flex items-center gap-1">
            <AudioLines className="h-[13px] w-[13px] text-primary-container" aria-hidden />
            Audio &amp; Query NLP engine
          </span>
          <span>v2.8 Bahasa-ID</span>
        </div>
      </SheetContent>
    </Sheet>
  );
}
