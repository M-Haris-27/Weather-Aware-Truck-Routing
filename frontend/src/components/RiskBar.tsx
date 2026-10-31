import type { RiskName } from "../api/types";
import { formatMiles } from "../lib/format";
import { RISK_COLORS, RISK_LABELS, RISK_ORDER } from "../lib/risk";

interface Props {
  miles: Record<RiskName, number>;
}

/** Stacked bar: share of the route's miles at each risk level. */
export default function RiskBar({ miles }: Props) {
  const total = RISK_ORDER.reduce((sum, level) => sum + miles[level], 0) || 1;
  const summary = RISK_ORDER.filter((l) => miles[l] > 0)
    .map((l) => `${RISK_LABELS[l]} ${formatMiles(miles[l])}`)
    .join(", ");
  return (
    <span className="riskbar" role="img" aria-label={`Miles by risk level: ${summary}`}>
      {RISK_ORDER.map(
        (level) =>
          miles[level] > 0 && (
            <span
              key={level}
              title={`${RISK_LABELS[level]}: ${formatMiles(miles[level])}`}
              style={{ width: `${(miles[level] / total) * 100}%`, background: RISK_COLORS[level] }}
            />
          ),
      )}
    </span>
  );
}
