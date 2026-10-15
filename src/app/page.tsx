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
            Hackathon demo — no login required
          </span>

          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-on-primary shadow-sm">
              <Radar className="h-7 w-7" aria-hidden />
            </div>
            <h1 className="text-kpi-stat tracking-tight text-on-surface">
              Demand Radar
            </h1>
          </div>

          <p className="text-headline-md font-normal leading-relaxed text-on-surface-variant">
            Demand Radar captures shopper demand that was never fulfilled — from
            kiosk conversations — and turns it into reorder recommendations for
            store managers. It contrasts Forecast A (POS only) against Forecast B
            (POS + unmet demand) to show why POS data alone misleads when shelves
            run dry. Open the kiosk, ask for coconut milk, then watch the signal
            reach the manager dashboard.
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
            Four scenarios that exercise the full loop. Reset any time.
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
  if (!href) {
    return (
      <span
        title="Belum tersedia"
        className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg border border-outline-variant bg-surface-container-low px-4 py-2 text-caption text-on-surface-variant opacity-60"
      >
        <Icon className="h-4 w-4" aria-hidden />
        {label}
      </span>
    );
  }
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
