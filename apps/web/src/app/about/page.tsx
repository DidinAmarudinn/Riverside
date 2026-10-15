import type { Metadata } from "next";
import {
  Cloud,
  Database,
  Globe,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { ResultsPanel } from "@/components/about/results-panel";

export const metadata: Metadata = {
  title: "About",
  description:
    "How Demand Radar works: architecture, platform roles and experiment results.",
};

const ROLES = [
  {
    icon: Cloud,
    title: "Cloud Run",
    body: "Hosts the FastAPI + ADK service behind the /api prefix: shopper agent, manager agent and the extraction endpoint.",
  },
  {
    icon: Sparkles,
    title: "Gemini (Vertex AI)",
    body: "Turns raw kiosk conversations into structured demand signals (SKU, outcome, confidence) and drafts manager explanations.",
  },
  {
    icon: Database,
    title: "BigQuery + BQML",
    body: "Stores stores, stock, POS and signals, and trains ARIMA_PLUS time-series models for Forecast A (POS only) and Forecast B (POS + unmet demand).",
  },
  {
    icon: Globe,
    title: "Firebase Hosting + Firestore",
    body: "Hosting serves this static frontend and rewrites /api/** to Cloud Run. Firestore pushes alerts, the live demand feed and KPIs to the dashboard in real time.",
  },
];

const FLOW = [
  "Kiosk shopper",
  "Cloud Run API + agents",
  "Pub/Sub → Gemini extract",
  "BigQuery + Forecast A/B",
  "Manager dashboard",
];

export default function AboutPage() {
  return (
    <PageShell>
      <div className="flex flex-col gap-8 py-10">
        <div className="max-w-3xl">
          <h1 className="text-kpi-stat tracking-tight text-on-surface">
            How Demand Radar works
          </h1>
          <p className="mt-2 text-body-default leading-relaxed text-on-surface-variant">
            Conversations at the kiosk become demand signals, signals become a
            corrected forecast, and the corrected forecast becomes a reorder
            recommendation the manager can act on.
          </p>
        </div>

        <section className="rounded-2xl bg-surface-container-lowest p-6 shadow-sm">
          <h2 className="mb-4 text-headline-md text-on-surface">
            Architecture
          </h2>
          <div className="flex flex-col items-stretch gap-3 lg:flex-row lg:items-center">
            {FLOW.map((step, i) => (
              <div key={step} className="flex flex-1 items-center gap-3">
                <div className="flex-1 rounded-xl border border-outline-variant bg-surface-container-low px-4 py-3 text-center text-body-medium text-on-surface">
                  {step}
                </div>
                {i < FLOW.length - 1 ? (
                  <ArrowRight
                    className="hidden h-5 w-5 flex-shrink-0 text-primary lg:block"
                    aria-hidden
                  />
                ) : null}
              </div>
            ))}
          </div>
          <p className="mt-4 text-caption text-on-surface-variant">
            Real-time updates (alerts, live demand feed, KPIs) come from
            read-only Firestore listeners scoped to each visitor&apos;s demo
            sandbox — see
            {" "}
            <code className="rounded bg-surface-container-low px-1 py-0.5 font-label-mono">
              docs/fe-decisions.md
            </code>
            .
          </p>
        </section>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {ROLES.map((role) => (
            <div
              key={role.title}
              className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-6 shadow-sm"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-container-high text-primary-container">
                <role.icon className="h-5 w-5" aria-hidden />
              </div>
              <h3 className="text-headline-sm text-on-surface">{role.title}</h3>
              <p className="text-body-default leading-relaxed text-on-surface-variant">
                {role.body}
              </p>
            </div>
          ))}
        </section>

        <section className="rounded-2xl bg-surface-container-lowest p-6 shadow-sm">
          <h2 className="text-headline-md text-on-surface">
            Experiment results
          </h2>
          <p className="mb-5 mt-1 text-caption text-on-surface-variant">
            Backtest against simulated ground truth: Forecast A vs. Forecast B.
          </p>
          <ResultsPanel />
        </section>
      </div>
    </PageShell>
  );
}
