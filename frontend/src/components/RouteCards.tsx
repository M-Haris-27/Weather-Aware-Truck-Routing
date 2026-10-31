import { memo } from "react";
import type { Route } from "../api/types";
import { formatDateTime, formatDuration, formatMiles, routeTitle } from "../lib/format";
import { routeColor } from "../lib/geojson";
import { RISK_COLORS, RISK_LABELS, RISK_ORDER } from "../lib/risk";
import RiskBar from "./RiskBar";

interface Props {
  routes: Route[];
  selectedId: string | null;
  recommendedId: string;
  reason: string;
  allBlocked: boolean;
  onSelect: (id: string) => void;
}

function RouteCards({ routes, selectedId, recommendedId, reason, allBlocked, onSelect }: Props) {
  const recommendedIndex = routes.findIndex((r) => r.id === recommendedId);
  const recommended = routes[recommendedIndex];

  return (
    <section aria-label="Route options">
      {recommended && (
        <div className={`reco ${allBlocked ? "warn" : ""}`}>
          <strong>
            {allBlocked ? "No safe route: " : "Recommended: "}
            {routeTitle(recommended.summary, recommendedIndex)}
          </strong>
          <span>{reason}</span>
        </div>
      )}

      <ul className="cards">
        {routes.map((route, i) => {
          const selected = route.id === selectedId;
          const issues = RISK_ORDER.filter((l) => l !== "LOW" && l !== "MODERATE" && route.miles_by_level[l] > 0);
          return (
            <li key={route.id}>
              <button
                type="button"
                className={`card ${selected ? "selected" : ""}`}
                aria-pressed={selected}
                onClick={() => onSelect(route.id)}
              >
                <span className="card-head">
                  <span className="swatch" style={{ background: routeColor(i) }} />
                  <span className="card-title">{routeTitle(route.summary, i)}</span>
                  {route.is_recommended && <span className="badge good">Recommended</span>}
                  {route.blocked && <span className="badge bad">No Travel</span>}
                </span>

                <span className="stats">
                  <span>
                    <small>Distance</small>
                    {formatMiles(route.distance_mi)}
                  </span>
                  <span>
                    <small>Drive time</small>
                    {formatDuration(route.duration_min)}
                  </span>
                  <span>
                    <small>Arrives</small>
                    {formatDateTime(route.arrival)}
                  </span>
                  <span>
                    <small>Avg risk</small>
                    {route.avg_risk.toFixed(2)} / 4
                  </span>
                </span>

                <RiskBar miles={route.miles_by_level} />

                <span className="levels">
                  {issues.length === 0 ? (
                    <span className="muted">No High-risk or worse stretches</span>
                  ) : (
                    issues.map((l) => (
                      <span key={l} className="level">
                        <i style={{ background: RISK_COLORS[l] }} />
                        {RISK_LABELS[l]} {formatMiles(route.miles_by_level[l])}
                      </span>
                    ))
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default memo(RouteCards);
