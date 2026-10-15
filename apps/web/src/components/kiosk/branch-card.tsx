import { Building2, Navigation, PackageCheck } from "lucide-react";
import type { KioskBranchCard } from "@/lib/api/types";

export function BranchCard({ branch }: { branch: KioskBranchCard }) {
  return (
    <div className="rounded-2xl border border-status-blue-border bg-gradient-to-r from-status-blue-bg/70 to-slate-50 p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3.5">
          <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-status-blue text-white shadow-md">
            <Building2 className="h-5 w-5" aria-hidden />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h5 className="text-sm font-bold text-slate-900">
                {branch.name}
              </h5>
              <span className="rounded-full border border-status-blue-border bg-status-blue-bg px-2 py-0.5 text-xs font-semibold text-status-blue">
                {branch.distanceKm.toLocaleString("id-ID")} km
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-600">
              Produk tersedia:{" "}
              <strong className="font-bold text-emerald-700">
                stok {branch.stockQty} pcs
              </strong>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled
            title="Segera hadir"
            className="tap-active flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-bold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-60"
          >
            <Navigation className="h-4 w-4 text-status-blue" aria-hidden />
            Lihat rute
          </button>
          <button
            type="button"
            disabled
            title="Segera hadir"
            className="tap-active flex items-center gap-1.5 rounded-xl bg-brand-teal px-3.5 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-brand-teal-dark disabled:opacity-60"
          >
            <PackageCheck className="h-4 w-4" aria-hidden />
            Minta kirim / simpan
          </button>
        </div>
      </div>
    </div>
  );
}
