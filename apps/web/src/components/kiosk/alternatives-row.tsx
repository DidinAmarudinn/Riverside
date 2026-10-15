import { Check, Package, MapPin } from "lucide-react";
import type { KioskProductCard } from "@/lib/api/types";
import { formatRupiah } from "@/lib/format";

export function AlternativesRow({
  alternatives,
}: {
  alternatives: KioskProductCard[];
}) {
  if (!alternatives.length) return null;

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600">
            Alternatif di toko ini
          </h4>
        </div>
        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
          Siap diambil sekarang
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
        {alternatives.map((alt) => (
          <div
            key={alt.sku}
            className="tap-active flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-teal-300 hover:shadow"
          >
            <div>
              <div className="mb-2 flex items-start justify-between gap-2">
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
                  <Check className="h-3 w-3 text-emerald-600" aria-hidden />
                  Tersedia
                </span>
                <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">
                  Stok {alt.stockQty ?? 0} pcs
                </span>
              </div>
              <div className="my-2 flex items-center gap-3">
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl border border-teal-100 bg-brand-teal-light text-brand-teal">
                  <Package className="h-6 w-6" aria-hidden />
                </div>
                <div>
                  <h5 className="text-sm font-bold leading-snug text-slate-900">
                    {alt.name}
                  </h5>
                  {alt.subtitle ? (
                    <p className="text-xs text-slate-500">{alt.subtitle}</p>
                  ) : null}
                </div>
              </div>
            </div>
            <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3">
              <div>
                <span className="block text-[11px] font-medium text-slate-400">
                  Harga
                </span>
                <span className="text-base font-extrabold text-brand-teal">
                  {alt.priceIdr != null ? formatRupiah(alt.priceIdr) : "—"}
                </span>
              </div>
              <div className="flex items-center gap-1.5 rounded-xl border border-status-amber-border bg-status-amber-bg px-3 py-1.5 text-xs font-bold text-amber-900">
                <MapPin className="h-3.5 w-3.5 text-amber-600" aria-hidden />
                {alt.aisle ?? "—"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
