import { Check, Radar, User } from "lucide-react";
import type { KioskMessage } from "@/hooks/use-kiosk-session";
import { formatTimeWib } from "@/lib/format";
import { ProductCard } from "./product-card";
import { AlternativesRow } from "./alternatives-row";
import { BranchCard } from "./branch-card";

function highlightPlaces(text: string) {
  const parts = text.split(/(Lorong \d+|Toko \d+ \([^)]+\))/g);
  return parts.map((part, i) =>
    /^(Lorong \d+|Toko \d+ \([^)]+\))$/.test(part) ? (
      <strong
        key={i}
        className="font-semibold text-teal-700 underline decoration-teal-400 underline-offset-2"
      >
        {part}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export function ShopperBubble({ message }: { message: KioskMessage }) {
  return (
    <div className="flex flex-col items-end gap-1.5 pl-12">
      <div className="flex max-w-[85%] items-end gap-2.5">
        <div className="rounded-2xl rounded-br-sm bg-brand-teal px-5 py-3.5 text-base font-medium leading-relaxed text-white shadow-md">
          {message.text}
        </div>
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-300 text-xs font-bold text-slate-600 shadow-sm">
          <User className="h-4 w-4" aria-hidden />
        </div>
      </div>
      <div className="flex items-center gap-1 pr-10 text-[11px] font-medium text-slate-400">
        <span>{formatTimeWib(message.ts)}</span>
        <Check className="h-3.5 w-3.5 text-teal-600" aria-hidden />
      </div>
    </div>
  );
}

export function AssistantBubble({ message }: { message: KioskMessage }) {
  if (message.role !== "assistant") return null;
  const { response } = message;

  return (
    <div className="flex flex-col items-start gap-3.5 pr-4">
      <div className="flex max-w-full items-start gap-3">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-brand-teal text-white shadow-md">
          <Radar className="h-5 w-5" aria-hidden />
        </div>
        <div className="flex-1 space-y-4">
          <div className="rounded-2xl rounded-tl-sm border border-slate-200/90 bg-white p-4 text-[15px] leading-relaxed text-slate-800 shadow-sm">
            <p>{highlightPlaces(response.reply)}</p>
          </div>

          {response.products.map((product) => (
            <ProductCard key={product.sku} product={product} />
          ))}

          <AlternativesRow alternatives={response.alternatives} />

          {response.nearestBranch ? (
            <BranchCard branch={response.nearestBranch} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
