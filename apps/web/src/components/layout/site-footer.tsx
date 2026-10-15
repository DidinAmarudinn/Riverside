import { Clock, Radar } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="mt-12 w-full bg-surface-container-lowest">
      <div className="mx-auto flex max-w-[1600px] flex-col items-center justify-between gap-4 px-8 py-8 md:flex-row">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-surface-container-low text-primary-container">
            <Radar className="h-4 w-4" aria-hidden />
          </div>
          <span className="text-headline-sm text-on-surface">Demand Radar</span>
          <span className="text-caption text-on-surface-variant">
            © {new Date().getFullYear()} · Hackathon demo build
          </span>
        </div>
        <div className="flex items-center gap-6 text-caption text-on-surface-variant">
          <span className="flex items-center gap-1.5">
            <Clock className="h-4 w-4 text-primary-container" aria-hidden />
            Timezone Asia/Jakarta
          </span>
          <span className="hidden items-center gap-1.5 sm:flex">
            Forecast A (POS) vs. Forecast B (POS + unmet demand)
          </span>
        </div>
      </div>
    </footer>
  );
}
