import { RISK_COLORS, RISK_LABELS, RISK_ORDER } from "../lib/risk";

export default function Legend() {
  return (
    <div className="legend" aria-label="Risk level legend">
      {RISK_ORDER.map((level) => (
        <span key={level}>
          <i style={{ background: RISK_COLORS[level] }} />
          {RISK_LABELS[level]}
        </span>
      ))}
    </div>
  );
}
