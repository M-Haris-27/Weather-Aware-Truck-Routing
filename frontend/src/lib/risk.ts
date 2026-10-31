import type { RiskName } from "../api/types";

export const RISK_ORDER: RiskName[] = ["LOW", "MODERATE", "HIGH", "SEVERE", "NO_TRAVEL"];

export const RISK_COLORS: Record<RiskName, string> = {
  LOW: "#22c55e",
  MODERATE: "#eab308",
  HIGH: "#f97316",
  SEVERE: "#dc2626",
  NO_TRAVEL: "#111827",
};

export const RISK_LABELS: Record<RiskName, string> = {
  LOW: "Low",
  MODERATE: "Moderate",
  HIGH: "High",
  SEVERE: "Severe",
  NO_TRAVEL: "No Travel",
};

export function riskFromLevel(level: number): RiskName {
  return RISK_ORDER[Math.max(0, Math.min(RISK_ORDER.length - 1, Math.round(level)))];
}
