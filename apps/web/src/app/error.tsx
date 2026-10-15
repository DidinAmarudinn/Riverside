"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[demand-radar] unhandled error", error);
  }, [error]);

  return (
    <PageShell>
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-error-container/50 text-error">
          <AlertTriangle className="h-7 w-7" aria-hidden />
        </div>
        <h1 className="text-headline-lg text-on-surface">Ada yang tidak berjalan</h1>
        <p className="max-w-md text-caption text-on-surface-variant">
          Terjadi kesalahan saat menampilkan halaman ini. Coba muat ulang.
        </p>
        <Button variant="primary" onClick={reset}>
          Coba lagi
        </Button>
      </div>
    </PageShell>
  );
}
