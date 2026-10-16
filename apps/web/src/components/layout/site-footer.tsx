import { RiverMark } from "./river-mark";
import { env } from "@/lib/env";

export function SiteFooter() {
  return (
    <footer className="mx-auto mt-10 w-full max-w-[1400px] px-4 pb-8 sm:px-8">
      <div className="flex flex-col items-start justify-between gap-3 border-t border-outline-variant pt-6 text-caption text-on-surface-variant md:flex-row md:items-center">
        <div className="flex items-center gap-2">
          <RiverMark className="h-6 w-6" />
          <span>Demand Radar by Team Riverside · Google Cloud AI Builder Cup 2026</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
          <span>All data is simulated · times in WIB (Asia/Jakarta)</span>
          {env.githubUrl ? (
            <a href={env.githubUrl} target="_blank" rel="noreferrer" className="font-semibold text-on-surface hover:underline">
              GitHub
            </a>
          ) : null}
        </div>
      </div>
    </footer>
  );
}
