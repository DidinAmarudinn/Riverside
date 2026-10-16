import type { KioskProductCard } from "@/lib/api/types";
import { formatRupiah } from "@/lib/format";
import { StatusTag } from "@/components/ui/status-tag";

export function AlternativesRow({ alternatives }: { alternatives: KioskProductCard[] }) {
  if (!alternatives.length) return null;
  return (
    <div className="flex flex-col gap-2">
      <span className="text-caption text-on-surface-variant">Alternatives in this store, ready to pick up</span>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {alternatives.map((alt) => (
          <div key={alt.sku} className="flex flex-col gap-1 rounded-xl bg-surface-container-lowest p-4">
            <div className="flex items-center justify-between gap-2">
              <StatusTag tone="green">In stock</StatusTag>
              <span className="text-caption text-on-surface-variant">{alt.stockQty ?? 0} pcs</span>
            </div>
            <h5 className="text-body-medium font-semibold text-on-surface">{alt.name}</h5>
            <p className="text-caption text-on-surface-variant">
              {alt.priceIdr != null ? formatRupiah(alt.priceIdr) : "—"}
              {alt.aisle ? ` · shelf ${alt.aisle}` : ""}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
