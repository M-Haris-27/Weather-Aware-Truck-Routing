import { memo } from "react";
import type { Route } from "../api/types";
import { formatShortDateTime } from "../lib/format";
import { RISK_COLORS, RISK_LABELS } from "../lib/risk";

interface Props {
  route: Route;
  title: string;
  onFocus: (routeId: string, index: number) => void;
}

function CheckpointTable({ route, title, onFocus }: Props) {
  return (
    <details className="checkpoints" open>
      <summary>
        Checkpoints · {title} <span className="muted">({route.checkpoints.length})</span>
      </summary>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Mile</th>
              <th>ETA</th>
              <th>Risk</th>
              <th>Wind</th>
              <th title="Rain, inches per hour">Rain</th>
              <th title="Snow, inches per hour">Snow</th>
            </tr>
          </thead>
          <tbody>
            {route.checkpoints.map((cp) => (
              <tr key={cp.index}>
                <td>
                  <button type="button" className="linklike" onClick={() => onFocus(route.id, cp.index)}>
                    {Math.round(cp.mile)}
                  </button>
                </td>
                <td>{formatShortDateTime(cp.eta)}</td>
                <td>
                  <span className="chip" style={{ background: RISK_COLORS[cp.risk] }} title={cp.reason}>
                    {RISK_LABELS[cp.risk]}
                  </span>
                </td>
                <td>{cp.wind_mph.toFixed(0)} mph</td>
                <td>{cp.rain_in_hr.toFixed(2)}</td>
                <td>{cp.snow_in_hr.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export default memo(CheckpointTable);
