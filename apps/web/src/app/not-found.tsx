import Link from "next/link";
import { Compass } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <PageShell>
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-container-high text-primary-container">
          <Compass className="h-7 w-7" aria-hidden />
        </div>
        <h1 className="text-headline-lg text-on-surface">Halaman tidak ditemukan</h1>
        <p className="max-w-md text-caption text-on-surface-variant">
          Tautan yang kamu buka tidak ada. Kembali ke halaman demo untuk memulai.
        </p>
        <div className="flex gap-2">
          <Link href="/">
            <Button variant="primary">Kembali ke beranda</Button>
          </Link>
          <Link href="/manager">
            <Button variant="outline">Buka dashboard</Button>
          </Link>
        </div>
      </div>
    </PageShell>
  );
}
