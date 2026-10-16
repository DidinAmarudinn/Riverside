import type { Metadata } from "next";
import {
  Cloud,
  Database,
  Globe,
  MessagesSquare,
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
    icon: MessagesSquare,
    title: "Gemini (Vertex AI)",
    body: "Runs both agents, reads the kiosk chats that rules cannot place into structured demand signals (SKU, outcome, confidence) and drafts manager explanations.",
  },
  {
    icon: Database,
    title: "BigQuery + BQML",
    body: "Stores stores, stock, POS and signals, and trains ARIMA_PLUS models for Forecast A (POS only) and Forecast B (POS + unmet demand).",
  },
  {
    icon: Globe,
    title: "Firebase Hosting + Firestore",
    body: "Hosting serves this static frontend and rewrites /api/** to Cloud Run. Firestore pushes alerts, the live demand feed and KPIs to the dashboard in real time.",
  },
];

const FLOW = [
  { title: "Shopper asks the kiosk", body: "Firebase Hosting serves the kiosk and dashboard." },
  { title: "Agents answer", body: "Cloud Run runs the ADK shopper and manager agents." },
  { title: "The chat becomes a signal", body: "Pub/Sub pushes each chat to the extractor; rules name the product and outcome, Gemini on Vertex AI takes the unclear chats." },
  { title: "Forecast A vs B", body: "BigQuery ML forecasts with and without the unmet demand." },
  { title: "Manager sees it live", body: "Firestore streams the feed and alerts to the dashboard." },
];

export default function AboutPage() {
  return (
    <PageShell>
      <div className="flex flex-col gap-4 pt-2">
        <div className="max-w-3xl">
          <h1 className="text-[30px] font-medium leading-tight tracking-[-0.03em] text-on-surface sm:text-[36px]">
            How Demand Radar works
          </h1>
          <p className="mt-2 text-body-default leading-relaxed text-on-surface-variant">
            Conversations at the kiosk become demand signals, signals become a
            corrected forecast, and the corrected forecast becomes a reorder
            recommendation the manager can act on.
          </p>
        </div>

        <section className="rounded-xl bg-surface-container-lowest p-6">
          <h2 className="mb-4 text-headline-md text-on-surface">
            From a chat to a reorder
          </h2>
          <ol className="grid grid-cols-1 gap-2.5 lg:grid-cols-5">
            {FLOW.map((step, i) => (
              <li key={step.title} className="flex flex-col gap-1 rounded-lg bg-surface-container-low p-4">
                <span className="flex items-center gap-2 text-body-medium text-on-surface">
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary text-[12px] font-semibold text-primary-fixed">
                    {i + 1}
                  </span>
                  {step.title}
                </span>
                <span className="text-caption text-on-surface-variant">{step.body}</span>
              </li>
            ))}
          </ol>
          <p className="mt-4 text-caption text-on-surface-variant">
            Real-time updates (alerts, live demand feed, KPIs) come from
            read-only Firestore listeners scoped to each visitor&apos;s private
            demo sandbox.
          </p>
        </section>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {ROLES.map((role) => (
            <div
              key={role.title}
              className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-6"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-low text-on-surface">
                <role.icon className="h-5 w-5" aria-hidden />
              </div>
              <h3 className="text-headline-sm text-on-surface">{role.title}</h3>
              <p className="text-body-default leading-relaxed text-on-surface-variant">
                {role.body}
              </p>
            </div>
          ))}
        </section>

        <section className="flex flex-col">
          <h2 className="text-headline-lg text-on-surface">
            Results
          </h2>
          <p className="mb-3 mt-1 text-caption text-on-surface-variant">
            Forecast A (POS only) vs. Forecast B (POS + unmet demand), scored against the simulator&apos;s true demand, and how well Gemini reads the chats.
          </p>
          <ResultsPanel />
        </section>
      </div>
    </PageShell>
  );
}
