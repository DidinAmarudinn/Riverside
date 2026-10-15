"use client";

import { useRouter } from "next/navigation";
import { FileText } from "lucide-react";
import type { Citation } from "@/lib/api/types";

export function CitationChip({ citation }: { citation: Citation }) {
  const router = useRouter();

  const handleClick = () => {
    if (!citation.sku) return;
    const params = new URLSearchParams({
      code: citation.sku,
      evidence: "open",
    });
    router.push(`/manager/sku?${params.toString()}`);
  };

  const interactive = Boolean(citation.sku);

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={!interactive}
      className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary-fixed/40 px-2.5 py-1 text-caption font-medium text-on-primary-fixed transition hover:bg-primary-fixed disabled:cursor-default disabled:opacity-70"
    >
      <FileText className="h-3.5 w-3.5" aria-hidden />
      {citation.label}
    </button>
  );
}
