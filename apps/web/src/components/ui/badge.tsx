import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeTone =
  | "neutral"
  | "primary"
  | "error"
  | "warning"
  | "success"
  | "info";

const tones: Record<BadgeTone, string> = {
  neutral: "bg-surface-container text-on-surface-variant",
  primary: "bg-primary-fixed text-on-primary-fixed",
  error: "bg-error-container/60 text-error",
  warning: "bg-secondary-fixed text-on-secondary-fixed-variant",
  success: "bg-status-green-bg text-status-green border border-status-green-border",
  info: "bg-surface-container-high text-primary",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: BadgeTone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 font-label-mono text-caption",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
