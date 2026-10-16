const JAKARTA = "Asia/Jakarta";

const idNumber = new Intl.NumberFormat("id-ID");

export function formatNumber(value: number): string {
  return idNumber.format(value);
}

/** `Rp 1.250.000` */
export function formatRupiah(value: number): string {
  return `Rp ${idNumber.format(Math.round(value))}`;
}

/** Compact currency for tight KPI space, e.g. `Rp 32.8M` (manager pages are in English). */
export function formatRupiahCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000_000) {
    return `Rp ${(value / 1_000_000_000).toLocaleString("en-US", {
      maximumFractionDigits: 1,
    })}B`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `Rp ${(value / 1_000_000).toLocaleString("en-US", {
      maximumFractionDigits: 1,
    })}M`;
  }
  return formatRupiah(value);
}

const timeParts = new Intl.DateTimeFormat("id-ID", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: JAKARTA,
});

/** `14:22` (colon separator, unlike the locale default of `14.22`). */
export function formatTimeWib(input: string | number | Date): string {
  const parts = timeParts.formatToParts(new Date(input));
  const hour = parts.find((p) => p.type === "hour")?.value ?? "00";
  const minute = parts.find((p) => p.type === "minute")?.value ?? "00";
  return `${hour}:${minute}`;
}

export function formatDateTimeWib(input: string | number | Date): string {
  const date = new Date(input);
  const datePart = new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    timeZone: JAKARTA,
  }).format(date);
  return `${datePart}, ${formatTimeWib(date)} WIB`;
}

export function formatDateWib(input: string | number | Date): string {
  const date = new Date(input);
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    timeZone: JAKARTA,
  }).format(date);
}

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

/** Relative time, e.g. "5 minutes ago". */
export function formatRelativeTime(input: string | number | Date): string {
  const then = new Date(input).getTime();
  const diffSeconds = Math.round((then - Date.now()) / 1000);
  const abs = Math.abs(diffSeconds);

  if (abs < 60) return rtf.format(diffSeconds, "second");
  const minutes = Math.round(diffSeconds / 60);
  if (Math.abs(minutes) < 60) return rtf.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return rtf.format(hours, "hour");
  const days = Math.round(hours / 24);
  return rtf.format(days, "day");
}

/** Percent helper, e.g. 0.64 -> "+64%". */
export function formatPercentDelta(
  value: number,
  { signed = true }: { signed?: boolean } = {},
): string {
  const pct = Math.round(value * 100);
  const sign = signed && pct > 0 ? "+" : "";
  return `${sign}${pct}%`;
}
