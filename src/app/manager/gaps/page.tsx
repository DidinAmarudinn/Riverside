import type { Metadata } from "next";
import { GapsView } from "./gaps-view";

export const metadata: Metadata = {
  title: "Assortment Gaps",
  description:
    "Products shoppers request but the store does not carry, ranked by request volume with category mix.",
};

export default function GapsPage() {
  return <GapsView />;
}
