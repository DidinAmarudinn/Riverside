"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * A single row that scrolls sideways: arrow buttons appear when there is more to see, and the mouse
 * wheel scrolls the row instead of the page while the pointer is over it.
 */
export function ScrollRow({ children, className }: { children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ left: false, right: false });

  const update = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    setEdges({ left: el.scrollLeft > 2, right: el.scrollLeft + el.clientWidth < el.scrollWidth - 2 });
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    const onWheel = (e: WheelEvent) => {
      if (el.scrollWidth <= el.clientWidth || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
      e.preventDefault();
      el.scrollLeft += e.deltaY;
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      ro.disconnect();
      el.removeEventListener("wheel", onWheel);
    };
  }, [update, children]);

  const nudge = (dir: 1 | -1) => ref.current?.scrollBy({ left: dir * ref.current.clientWidth * 0.7, behavior: "smooth" });

  return (
    <div className={cn("relative min-w-0", className)}>
      <div ref={ref} onScroll={update} className="no-scrollbar flex gap-1.5 overflow-x-auto scroll-smooth">
        {children}
      </div>
      {edges.left ? (
        <button
          type="button"
          aria-label="Scroll left"
          onClick={() => nudge(-1)}
          className="absolute inset-y-0 left-0 flex w-10 items-center justify-start bg-gradient-to-r from-surface-container-lowest via-surface-container-lowest/90 to-transparent"
        >
          <ChevronLeft className="h-7 w-7 rounded-full bg-surface-container-lowest p-1 text-on-surface shadow-[0_1px_4px_rgba(14,42,32,0.2)]" aria-hidden />
        </button>
      ) : null}
      {edges.right ? (
        <button
          type="button"
          aria-label="Scroll right"
          onClick={() => nudge(1)}
          className="absolute inset-y-0 right-0 flex w-10 items-center justify-end bg-gradient-to-l from-surface-container-lowest via-surface-container-lowest/90 to-transparent"
        >
          <ChevronRight className="h-7 w-7 rounded-full bg-surface-container-lowest p-1 text-on-surface shadow-[0_1px_4px_rgba(14,42,32,0.2)]" aria-hidden />
        </button>
      ) : null}
    </div>
  );
}
