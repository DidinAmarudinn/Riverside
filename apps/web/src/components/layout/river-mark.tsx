import { cn } from "@/lib/utils";

/**
 * Team Riverside's "River Forecast" app icon: the solid line is sales history, the dots are the forecast,
 * the lime dot is the target. Same drawing as app/icon.svg (the favicon).
 */
export function RiverMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" aria-hidden className={cn("h-8 w-8 shrink-0", className)}>
      <rect width="120" height="120" rx="28" fill="#1F8A5B" />
      <path d="M18 98 C 32 98 38 91 50 91 C 62 91 66 98 80 98" fill="none" stroke="#fff" strokeOpacity=".45" strokeWidth="6" strokeLinecap="round" />
      <path d="M16 78 C 30 78 34 58 48 58 C 61 58 63 72 76 67" fill="none" stroke="#fff" strokeWidth="11" strokeLinecap="round" />
      <path d="M76 67 C 86 62 92 52 97 41" fill="none" stroke="#fff" strokeWidth="11" strokeLinecap="round" strokeDasharray="0.01 16" />
      <circle cx="102" cy="27" r="9" fill="#B7E36A" />
    </svg>
  );
}
