import { describe, expect, it } from "vitest";
import {
  formatNumber,
  formatPercentDelta,
  formatRupiah,
  formatRupiahCompact,
  formatTimeWib,
} from "./format";

describe("format", () => {
  it("formats IDR with thousand separators", () => {
    expect(formatRupiah(1_250_000)).toBe("Rp 1.250.000");
    expect(formatNumber(1234)).toBe("1.234");
  });

  it("formats compact IDR", () => {
    expect(formatRupiahCompact(32_800_000)).toBe("Rp 32.8M");
    expect(formatRupiahCompact(1_500_000_000)).toBe("Rp 1.5B");
  });

  it("formats signed percentages", () => {
    expect(formatPercentDelta(0.64)).toBe("+64%");
    expect(formatPercentDelta(-0.1)).toBe("-10%");
  });

  it("formats time in Asia/Jakarta", () => {
    // 07:22 UTC == 14:22 WIB
    expect(formatTimeWib("2026-10-13T07:22:00.000Z")).toBe("14:22");
  });
});
