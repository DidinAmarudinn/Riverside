"use client";

import { useState } from "react";
import { Camera, Mic, Send, X } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { env } from "@/lib/env";
import { cn } from "@/lib/utils";

export function ChatInput({
  disabled,
  onSend,
}: {
  disabled?: boolean;
  onSend: (text: string) => void;
}) {
  const [value, setValue] = useState("");

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  const multimodalEnabled = env.featureMultimodal;

  return (
    <div className="space-y-3.5">
      <div className="flex items-center gap-3">
        <MultimodalButton
          label="Foto"
          icon={Camera}
          enabled={multimodalEnabled}
        />
        <MultimodalButton
          label="Suara"
          icon={Mic}
          enabled={multimodalEnabled}
          amber
        />

        <div className="relative flex-1">
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") submit();
            }}
            disabled={disabled}
            placeholder="Ketik barang yang kamu cari…"
            aria-label="Ketik barang yang kamu cari"
            className="h-14 w-full rounded-2xl border-2 border-slate-200 bg-slate-50 pl-5 pr-12 text-base font-medium text-slate-800 placeholder-slate-400 shadow-inner transition focus:border-brand-teal focus:bg-white focus:outline-none disabled:opacity-60"
          />
          {value ? (
            <button
              type="button"
              onClick={() => setValue("")}
              aria-label="Bersihkan input"
              className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 text-slate-400 transition hover:text-slate-600"
            >
              <X className="h-5 w-5" />
            </button>
          ) : null}
        </div>

        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="tap-active flex h-14 flex-shrink-0 items-center justify-center gap-2 rounded-2xl bg-brand-teal px-7 text-base font-bold text-white shadow-md transition hover:bg-brand-teal-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span>Kirim</span>
          <Send className="h-5 w-5 -rotate-45" aria-hidden />
        </button>
      </div>

      <div className="flex items-center justify-between px-1 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full bg-teal-500" />
          <span>Layar sentuh aktif • ketuk mikrofon untuk pencarian suara</span>
        </div>
        <span className="hidden sm:block">Demand Radar kiosk</span>
      </div>
    </div>
  );
}

function MultimodalButton({
  label,
  icon: Icon,
  enabled,
  amber = false,
}: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  enabled: boolean;
  amber?: boolean;
}) {
  const button = (
    <button
      type="button"
      disabled
      title="Segera hadir"
      aria-label={`${label} — segera hadir`}
      className={cn(
        "tap-active flex h-14 w-14 flex-shrink-0 flex-col items-center justify-center rounded-2xl border-2 shadow-sm transition disabled:opacity-60",
        amber
          ? "border-status-amber-border bg-status-amber-bg text-amber-700"
          : "border-slate-200 bg-slate-100 text-slate-700",
      )}
    >
      <Icon className="h-6 w-6" />
      <span className="mt-0.5 text-[9px] font-bold">{label}</span>
    </button>
  );

  if (enabled) return button;

  return (
    <Tooltip>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent>Segera hadir</TooltipContent>
    </Tooltip>
  );
}
