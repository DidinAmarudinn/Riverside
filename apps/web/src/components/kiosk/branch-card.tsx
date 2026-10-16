import type { KioskBranchCard } from "@/lib/api/types";

export function BranchCard({ branch }: { branch: KioskBranchCard }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl bg-primary p-4 text-on-primary">
      <div className="flex items-center justify-between gap-2">
        <span className="text-caption text-white/70">Nearest branch with stock</span>
        <span className="rounded-full bg-primary-fixed px-2.5 py-1 text-caption font-semibold text-on-primary-fixed">
          {branch.distanceKm.toLocaleString("en-US")} km
        </span>
      </div>
      <h5 className="text-body-medium font-semibold">{branch.name}</h5>
      <p className="text-caption text-white/70">{branch.stockQty} pcs available there</p>
    </div>
  );
}
