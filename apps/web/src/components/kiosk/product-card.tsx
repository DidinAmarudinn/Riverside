import { Check, Package, PackageX } from "lucide-react";
import type { KioskProductCard } from "@/lib/api/types";
import { formatRupiah } from "@/lib/format";
import { cn } from "@/lib/utils";

export function ProductCard({ product }: { product: KioskProductCard }) {
  const out = !product.inStock;
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border-2 bg-white p-4 shadow-sm",
        out ? "border-status-red-border" : "border-status-green-border",
      )}
    >
      <div
        className={cn(
          "absolute left-0 top-0 h-full w-2",
          out ? "bg-status-red" : "bg-status-green",
        )}
      />
      <div className="pl-2">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            {out ? "Barang yang dicari" : "Barang"}
          </span>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold",
              out
                ? "border-status-red-border bg-status-red-bg text-status-red"
                : "border-status-green-border bg-status-green-bg text-status-green",
            )}
          >
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                out ? "bg-status-red" : "bg-status-green",
              )}
            />
            {out ? "Habis" : "Tersedia"}
          </span>
        </div>

        <div className="flex items-center gap-3.5">
          <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-100 text-slate-400">
            {out ? (
              <PackageX className="h-7 w-7 text-status-red" aria-hidden />
            ) : (
              <Package className="h-7 w-7 text-brand-teal" aria-hidden />
            )}
          </div>
          <div className="flex-1">
            <h3 className="text-base font-bold leading-snug text-slate-800">
              {product.name}
            </h3>
            {product.subtitle ? (
              <p className="mt-0.5 text-xs text-slate-500">
                {product.subtitle}
              </p>
            ) : null}
            <div className="mt-1.5 flex items-center gap-3 text-xs">
              {product.priceIdr != null ? (
                <span className="font-medium text-slate-500">
                  {formatRupiah(product.priceIdr)}
                </span>
              ) : null}
              <span className="text-slate-400">
                {out ? "Stok toko saat ini:" : "Stok:"}{" "}
                <strong className={out ? "text-status-red" : "text-status-green"}>
                  {product.stockQty ?? 0} pcs
                </strong>
              </span>
            </div>
          </div>
        </div>

        {out ? (
          <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2.5 text-[11px] text-slate-500">
            <div className="flex items-center gap-1.5 font-medium text-teal-700">
              <Check className="h-3.5 w-3.5 text-teal-600" aria-hidden />
              Permintaan dicatat ke sistem Demand Radar
            </div>
            <span className="font-mono text-slate-400">
              #{product.sku}
            </span>
          </div>
        ) : null}
      </div>
    </div>
  );
}
