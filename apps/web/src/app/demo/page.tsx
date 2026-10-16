import type { Metadata } from "next";
import { PageShell } from "@/components/layout/page-shell";
import { LiveDemo } from "./live-demo";

export const metadata: Metadata = {
  title: "Live demo",
  description:
    "Ask the kiosk for something sold out and follow the request through Pub/Sub and Gemini to the manager's dashboard.",
};

export default function DemoPage() {
  return (
    <PageShell>
      <LiveDemo />
    </PageShell>
  );
}
