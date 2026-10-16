import { Skeleton } from "@/components/ui/skeleton";

/** Shown while the dashboard's data is on its way: the same cards as the page, pulsing where numbers go. */
export function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy>
      <div className="flex flex-col justify-between gap-4 pt-2 md:flex-row md:items-center">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-72 bg-surface-container-lowest" />
          <Skeleton className="h-4 w-96 max-w-full bg-surface-container-lowest" />
        </div>
        <Skeleton className="h-11 w-56 rounded-full bg-surface-container-lowest" />
      </div>
      <DecisionBannerSkeleton />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <KpiSkeleton key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-12">
        <div className="flex flex-col gap-4 rounded-xl bg-surface-container-lowest p-6 lg:col-span-8">
          <Skeleton className="h-7 w-48" />
          <div className="flex gap-2">
            {[56, 80, 96, 72, 84].map((w) => (
              <Skeleton key={w} className="h-8 rounded-full" style={{ width: w }} />
            ))}
          </div>
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
        <div className="flex flex-col gap-4 lg:col-span-4">
          {[0, 1].map((i) => (
            <div key={i} className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-6">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-16 w-full rounded-lg" />
              <Skeleton className="h-16 w-full rounded-lg" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function DecisionBannerSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-xl bg-primary p-6" aria-hidden>
      <span className="h-4 w-32 animate-pulse rounded bg-white/10" />
      <span className="h-8 w-2/3 animate-pulse rounded-md bg-white/10" />
      <span className="h-4 w-1/2 animate-pulse rounded bg-white/10" />
    </div>
  );
}

function KpiSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-5" aria-hidden>
      <div className="flex items-center gap-2.5">
        <Skeleton className="h-9 w-9 rounded-full" />
        <Skeleton className="h-4 w-32" />
      </div>
      <Skeleton className="h-10 w-24" />
      <Skeleton className="h-4 w-3/4" />
    </div>
  );
}

/** Shown while a product's data is on its way. */
export function SkuSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy>
      <div className="flex flex-col gap-2 pt-2">
        <Skeleton className="h-4 w-28 bg-surface-container-lowest" />
        <Skeleton className="h-10 w-80 max-w-full bg-surface-container-lowest" />
        <Skeleton className="h-4 w-64 bg-surface-container-lowest" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <KpiSkeleton key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-12">
        <div className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-6 lg:col-span-8">
          <Skeleton className="h-7 w-52" />
          <Skeleton className="h-4 w-80 max-w-full" />
          <Skeleton className="h-[240px] w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
        </div>
        <div className="flex flex-col gap-4 lg:col-span-4">
          <div className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-6">
            <Skeleton className="h-6 w-48" />
            <div className="grid grid-cols-2 gap-3">
              <Skeleton className="h-28 rounded-lg" />
              <Skeleton className="h-28 rounded-lg" />
            </div>
            <Skeleton className="h-24 w-full" />
          </div>
          <div className="flex flex-col gap-2 rounded-xl bg-surface-container-lowest p-6">
            <Skeleton className="h-6 w-40" />
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-11 w-full rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
