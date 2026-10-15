import { AlertCircle, Inbox, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function InlineSpinner({ className }: { className?: string }) {
  return (
    <Loader2 className={cn("h-4 w-4 animate-spin", className)} aria-hidden />
  );
}

export function LoadingBlock({
  label = "Memuat data…",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      role="status"
      className={cn(
        "flex items-center justify-center gap-2 py-10 text-caption text-on-surface-variant",
        className,
      )}
    >
      <InlineSpinner />
      {label}
    </div>
  );
}

export function CardSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
}: {
  title: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-surface-container text-on-surface-variant">
        <Icon className="h-5 w-5" aria-hidden />
      </div>
      <p className="text-body-medium text-on-surface">{title}</p>
      {description ? (
        <p className="max-w-sm text-caption text-on-surface-variant">
          {description}
        </p>
      ) : null}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Terjadi kesalahan",
  description,
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-error-container/50 text-error">
        <AlertCircle className="h-5 w-5" aria-hidden />
      </div>
      <div>
        <p className="text-body-medium text-on-surface">{title}</p>
        {description ? (
          <p className="mt-1 max-w-sm text-caption text-on-surface-variant">
            {description}
          </p>
        ) : null}
      </div>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Coba lagi
        </Button>
      ) : null}
    </div>
  );
}
