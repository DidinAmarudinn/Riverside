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
        className="font-semibold text-on-surface underline decoration-primary-fixed decoration-2 underline-offset-2"
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
    <div className="flex flex-col items-end gap-1 pl-10">
      <div className="max-w-[85%] rounded-[20px] rounded-br-md bg-primary px-4 py-3 text-body-default text-on-primary">
        {message.text}
      </div>
      <span className="text-[11px] text-on-surface-variant">{formatTimeWib(message.ts)}</span>
    </div>
  );
}

export function AssistantBubble({ message }: { message: KioskMessage }) {
  if (message.role !== "assistant") return null;
  const { response } = message;

  return (
    <div className="flex flex-col items-start gap-3 pr-2 sm:pr-8">
      <div className="max-w-[92%] rounded-[20px] rounded-bl-md bg-surface-container-lowest px-4 py-3 text-body-default leading-relaxed whitespace-pre-line text-on-surface">
        {highlightPlaces(response.reply)}
      </div>
      <div className="flex w-full flex-col gap-2">
        {response.products.map((product) => (
          <ProductCard key={product.sku} product={product} />
        ))}
        <AlternativesRow alternatives={response.alternatives} />
        {response.nearestBranch ? <BranchCard branch={response.nearestBranch} /> : null}
      </div>
    </div>
  );
}
