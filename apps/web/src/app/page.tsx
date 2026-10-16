import type { Metadata } from "next";
import { Code2, PlayCircle, Radar, Sparkles } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { JuryActions } from "./jury-actions";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "Demand Radar",
  description:
    "Demand Radar turns unmet shopper demand into reorder recommendations. Forecast A (POS only) vs. Forecast B (POS + unmet demand).",
};

export default function HomePage() {
  return (
    <PageShell>
      <section className="flex flex-col gap-8 py-10">
        <div className="flex max-w-3xl flex-col gap-5">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-primary/20 bg-surface-container-low px-3 py-1.5 text-caption font-medium text-primary">
            <Sparkles className="h-4 w-4" aria-hidden />
            Google Cloud AI Builder Cup 2026 · no login required
          </span>

          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-on-primary shadow-sm">
              <Radar className="h-7 w-7" aria-hidden />
            </div>
            <h1 className="text-kpi-stat tracking-tight text-on-surface">
              Demand Radar
            </h1>
          </div>

          <p className="text-headline-md font-normal leading-relaxed text-on-surface">
            POS data tells you what sold. Conversations tell you what people
            wanted.
          </p>
          <p className="max-w-2xl text-body-default leading-relaxed text-on-surface-variant">
            When a shelf is empty, the till records zero and the forecast orders
            less. Demand Radar listens to shopper chats at a store kiosk, uses
            Gemini to turn each request into a product and an outcome, and
            corrects the reorder with the demand the POS never saw.
          </p>
          <p className="text-caption text-on-surface-variant">
            All stores, stock, sales and conversations are simulated for this
            demo.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <ResourceLink
              href={env.videoUrl}
              icon={PlayCircle}
              label="Watch the video"
            />
            <ResourceLink href={env.githubUrl} icon={Code2} label="GitHub repo" />
          </div>
        </div>

        <div className="rounded-2xl bg-surface-container-lowest p-6 shadow-sm">
          <h2 className="mb-1 text-headline-md text-on-surface">
            Try the demo
          </h2>
          <p className="mb-5 text-caption text-on-surface-variant">
            Four steps through the full loop, in your own private sandbox.
          </p>
          <JuryActions />
        </div>
      </section>
    </PageShell>
  );
}

function ResourceLink({
  href,
  icon: Icon,
  label,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-2 rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-2 text-caption font-medium text-on-surface transition hover:bg-surface-container-low"
    >
      <Icon className="h-4 w-4 text-primary" aria-hidden />
      {label}
    </a>
  );
}
