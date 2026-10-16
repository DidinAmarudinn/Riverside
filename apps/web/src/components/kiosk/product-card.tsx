import type { KioskProductCard } from "@/lib/api/types";
import { formatRupiah } from "@/lib/format";
import { StatusTag } from "@/components/ui/status-tag";

export function ProductCard({ product }: { product: KioskProductCard }) {
  const out = !product.inStock;
  return (
    <div className="flex flex-col gap-1 rounded-xl bg-surface-container-lowest p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-caption text-on-surface-variant">{out ? "You asked for" : "Product"}</span>
        <StatusTag tone={out ? "red" : "green"}>{out ? "Out of stock" : "In stock"}</StatusTag>
      </div>
      <h3 className="text-body-medium font-semibold text-on-surface">{product.name}</h3>
      {product.subtitle ? <p className="text-caption text-on-surface-variant">{product.subtitle}</p> : null}
      <p className="text-caption text-on-surface-variant">
        {product.priceIdr != null ? `${formatRupiah(product.priceIdr)} · ` : ""}
        {product.stockQty ?? 0} in this store
        {product.aisle && !out ? ` · shelf ${product.aisle}` : ""}
        {out ? " · request logged to Demand Radar" : ""}
      </p>
    </div>
  );
}
