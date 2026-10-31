import { addHours, formatDateTime } from "../lib/format";

interface Props {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  hour: number;
  maxHour: number;
  onHourChange: (hour: number) => void;
  start: string;
}

/** Weather-risk heatmap toggle and 0-48 h forecast slider. */
export default function HeatmapControl({ enabled, onToggle, hour, maxHour, onHourChange, start }: Props) {
  return (
    <div className="heat-control">
      <div className="heat-top">
        <label className="toggle">
          <input type="checkbox" checked={enabled} onChange={(e) => onToggle(e.target.checked)} />
          Weather heatmap
        </label>
        <span className="heat-time" aria-live="polite">
          {hour === 0 ? "Departure" : `+${hour}h`} · {formatDateTime(addHours(start, hour))}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={maxHour}
        step={1}
        value={hour}
        disabled={!enabled}
        aria-label="Forecast hour after departure"
        aria-valuetext={`${hour} hours after departure`}
        onChange={(e) => onHourChange(Number(e.target.value))}
      />
      <div className="ticks" aria-hidden="true">
        {[0, 12, 24, 36, 48].filter((t) => t <= maxHour).map((t) => (
          <span key={t}>{t}h</span>
        ))}
      </div>
    </div>
  );
}
