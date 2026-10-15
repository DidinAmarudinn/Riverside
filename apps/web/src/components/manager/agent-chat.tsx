"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Bot,
  ChevronsDownUp,
  Maximize2,
  Send,
  Sparkles,
} from "lucide-react";
import { useAgentChat } from "@/hooks/use-agent-chat";
import { useStore } from "@/hooks/use-store";
import { sampleQuestions } from "@/mocks/chat";
import { cn } from "@/lib/utils";
import { InlineSpinner } from "@/components/common/states";
import { CitationChip } from "./citation-chip";

export function AgentChat({
  initialQuestion,
  sku,
  className,
}: {
  initialQuestion?: string;
  sku?: string;
  className?: string;
}) {
  const { storeId } = useStore();
  const { messages, send, isSending, error } = useAgentChat(storeId, sku);
  const [collapsed, setCollapsed] = useState(false);
  const [input, setInput] = useState("");
  const bodyRef = useRef<HTMLDivElement>(null);
  const sentInitial = useRef(false);

  useEffect(() => {
    if (initialQuestion && !sentInitial.current) {
      sentInitial.current = true;
      void send(initialQuestion);
    }
  }, [initialQuestion, send]);

  useEffect(() => {
    bodyRef.current?.scrollTo({
      top: bodyRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, isSending]);

  const submit = (text: string) => {
    const value = text.trim();
    if (!value || isSending) return;
    void send(value);
    setInput("");
  };

  return (
    <div
      className={cn(
        "w-96 max-w-[calc(100vw-2rem)] rounded-xl bg-surface-container-lowest shadow-xl",
        className,
      )}
    >
      <div className="flex items-center justify-between rounded-t-xl bg-surface-container-low p-3.5">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-on-primary">
            <Bot className="h-[18px] w-[18px]" aria-hidden />
          </div>
          <div className="flex flex-col">
            <span className="text-headline-sm leading-tight text-on-surface">
              Ask Demand Radar AI
            </span>
            <span className="text-[11px] leading-none text-on-surface-variant">
              Telemetry &amp; Anomaly Intelligence
            </span>
          </div>
        </div>
        <button
          type="button"
          aria-label={collapsed ? "Buka panel" : "Penyatukan panel"}
          onClick={() => setCollapsed((v) => !v)}
          className="rounded p-1 text-on-surface-variant transition hover:text-on-surface"
        >
          {collapsed ? (
            <Maximize2 className="h-[18px] w-[18px]" />
          ) : (
            <ChevronsDownUp className="h-[18px] w-[18px]" />
          )}
        </button>
      </div>

      {!collapsed ? (
        <div className="flex flex-col gap-2 p-4">
          {messages.length === 0 ? (
            <>
              <p className="text-caption text-on-surface-variant">
                Instant insights on lost revenue and demand anomalies.
              </p>
              <div className="my-1 flex flex-col gap-1.5">
                {sampleQuestions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => submit(q)}
                    className="flex items-center justify-between rounded-lg bg-surface-container px-2.5 py-1.5 text-left text-caption text-on-surface transition hover:bg-surface-container-high"
                  >
                    <span>“{q}”</span>
                    <ArrowRight className="h-[14px] w-[14px] text-primary" aria-hidden />
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div
              ref={bodyRef}
              className="flex max-h-72 flex-col gap-2.5 overflow-y-auto pr-1"
            >
              {messages.map((m) =>
                m.role === "user" ? (
                  <div
                    key={m.id}
                    className="self-end rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-caption text-on-primary"
                  >
                    {m.text}
                  </div>
                ) : (
                  <div
                    key={m.id}
                    className="rounded-2xl rounded-tl-sm bg-surface-container-low p-2.5 text-caption text-on-surface"
                  >
                    <div className="mb-1 flex items-center gap-1 font-semibold text-primary">
                      <Sparkles className="h-[14px] w-[14px]" aria-hidden />
                      Demand Radar Insights
                    </div>
                    <p className="leading-relaxed">{m.text}</p>
                    {m.citations.length ? (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {m.citations.map((c, i) => (
                          <CitationChip key={i} citation={c} />
                        ))}
                      </div>
                    ) : null}
                  </div>
                ),
              )}
              {isSending ? (
                <div className="flex items-center gap-2 text-caption text-on-surface-variant">
                  <InlineSpinner /> Menganalisis…
                </div>
              ) : null}
            </div>
          )}

          {error ? (
            <p className="text-caption text-error">{error}</p>
          ) : null}

          <div className="mt-1 flex items-center gap-1">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submit(input);
              }}
              placeholder="Ask anything about store demand…"
              className="flex-1 rounded-lg bg-surface-container-low px-3 py-2 text-caption text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              type="button"
              aria-label="Kirim pertanyaan"
              onClick={() => submit(input)}
              disabled={isSending}
              className="flex items-center justify-center rounded-lg bg-primary p-2 text-on-primary transition hover:bg-primary-container disabled:opacity-50"
            >
              <Send className="h-[18px] w-[18px]" aria-hidden />
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
