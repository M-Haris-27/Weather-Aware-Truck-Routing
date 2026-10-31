import { describe, expect, it } from "vitest";
import { RISK_COLORS, RISK_LABELS, RISK_ORDER, riskFromLevel } from "./risk";

describe("risk helpers", () => {
  it("maps numeric levels to names, clamping out-of-range values", () => {
    expect(riskFromLevel(0)).toBe("LOW");
    expect(riskFromLevel(3)).toBe("SEVERE");
    expect(riskFromLevel(4)).toBe("NO_TRAVEL");
    expect(riskFromLevel(9)).toBe("NO_TRAVEL");
    expect(riskFromLevel(-2)).toBe("LOW");
  });

  it("has a color and label for every level", () => {
    for (const level of RISK_ORDER) {
      expect(RISK_COLORS[level]).toMatch(/^#[0-9a-f]{6}$/i);
      expect(RISK_LABELS[level].length).toBeGreaterThan(0);
    }
  });
});
