"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  MessageSquareText,
  Send,
  X,
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
  // Starts closed so it does not cover the feed; the jury link (?q=) opens it with the question.
  const [collapsed, setCollapsed] = useState(!initialQuestion);
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

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={() => setCollapsed(false)}
        className={cn(
          "flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-body-medium font-semibold text-on-primary shadow-[0_8px_24px_rgba(14,42,32,0.25)] transition hover:bg-[#1c3d30]",
          className,
        )}
      >
        <MessageSquareText className="h-[18px] w-[18px]" aria-hidden />
        Ask why
      </button>
    );
  }

  return (
    <div
      className={cn(
        "w-96 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl bg-surface-container-lowest shadow-[0_12px_40px_rgba(14,42,32,0.18)]",
        className,
      )}
    >
      <div className="flex items-center justify-between bg-primary px-4 py-3.5 text-on-primary">
        <div className="flex flex-col">
          <span className="text-headline-sm leading-tight">Ask why</span>
          <span className="text-[11px] leading-none text-white/70">Gemini agent · answers cite the data</span>
        </div>
        <button
          type="button"
          aria-label="Close panel"
          onClick={() => setCollapsed(true)}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 transition hover:bg-white/20"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      {!collapsed ? (
        <div className="flex flex-col gap-2 p-4">
          {messages.length === 0 ? (
            <>
              <p className="text-caption text-on-surface-variant">
                Ask about lost sales, stockouts and what shoppers want. Answers cite the data they use.
              </p>
              <div className="my-1 flex flex-col gap-1.5">
                {sampleQuestions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => submit(q)}
                    className="flex items-center justify-between rounded-xl bg-surface-container-low px-3 py-2 text-left text-caption text-on-surface transition hover:bg-surface-container-high"
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
              className="flex-1 rounded-full bg-surface-container-low px-4 py-2.5 text-caption text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              type="button"
              aria-label="Kirim pertanyaan"
              onClick={() => submit(input)}
              disabled={isSending}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-on-primary transition hover:bg-[#1c3d30] disabled:opacity-50"
            >
              <Send className="h-[18px] w-[18px]" aria-hidden />
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
