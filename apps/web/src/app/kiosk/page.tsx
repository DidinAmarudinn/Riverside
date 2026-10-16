import type { Metadata } from "next";
import { PageShell } from "@/components/layout/page-shell";
import { KioskChat } from "./kiosk-chat";

export const metadata: Metadata = {
  title: "Kiosk Shopper",
  description:
    "Chat with the in-store shopper assistant: check stock, get alternatives and the nearest branch with stock.",
};

export default function KioskPage() {
  return (
    <PageShell>
      <KioskChat />
    </PageShell>
  );
}
