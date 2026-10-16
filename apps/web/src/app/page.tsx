import type { Metadata } from "next";
import Link from "next/link";
import { PageShell } from "@/components/layout/page-shell";
import { JuryActions } from "./jury-actions";
import { HeroStory } from "@/components/home/hero-story";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "Demand Radar",
  description:
    "Demand Radar turns unmet shopper demand into reorder recommendations. Forecast A (POS only) vs. Forecast B (POS + unmet demand).",
};

export default function HomePage() {
  return (
    <PageShell>
      <div className="flex flex-col gap-8">
        <div className="grid grid-cols-1 items-stretch gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div className="flex min-w-0 flex-col justify-center gap-5 rounded-xl bg-surface-container-lowest p-6 sm:p-8">
            <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-status-green-bg px-3 py-1 text-caption font-semibold text-status-green">
              <span className="h-1.5 w-1.5 rounded-full bg-current" />
              Google Cloud AI Builder Cup 2026
            </span>
            <h1 className="text-[32px] font-medium leading-[1.08] tracking-[-0.03em] text-on-surface sm:text-[44px]">
              POS data tells you what sold.{" "}
              <span className="text-primary-container">Conversations tell you what people wanted.</span>
            </h1>
            <p className="max-w-xl text-body-default leading-relaxed text-on-surface-variant">
              When a shelf is empty, the till records zero and the forecast orders less. Demand Radar listens
              to shopper chats at a store kiosk, turns each request into a product and an outcome (Gemini reads the unclear ones),
              and corrects the reorder with the demand the POS never saw.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href="/demo"
                className="rounded-full bg-primary px-5 py-3 text-body-medium font-semibold text-on-primary transition hover:bg-[#1c3d30]"
              >
                Try the live demo
              </Link>
              {env.videoUrl ? (
                <a
                  href={env.videoUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-full px-5 py-3 text-body-medium font-semibold text-on-surface shadow-[inset_0_0_0_1.5px_var(--color-outline-variant)] hover:bg-surface-container-low"
                >
                  Watch the video
                </a>
              ) : null}
            </div>
            <p className="text-caption text-on-surface-variant">
              All stores, stock, sales and conversations are simulated.
            </p>
          </div>

          <HeroStory />
        </div>

        <JuryActions />
      </div>
    </PageShell>
  );
}
