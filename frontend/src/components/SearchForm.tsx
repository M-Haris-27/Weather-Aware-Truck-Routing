import { memo, useState } from "react";
import type { AnalyzeRequest, PlaceRef } from "../api/types";
import { fromLocalInput, nextFullHour, toLocalInputValue } from "../lib/format";
import PlaceInput from "./PlaceInput";

const MAX_LOAD_LB = 120_000;

interface Props {
  loading: boolean;
  onSubmit: (request: AnalyzeRequest) => void;
}

function SearchForm({ loading, onSubmit }: Props) {
  const [originText, setOriginText] = useState("");
  const [origin, setOrigin] = useState<PlaceRef | null>(null);
  const [destText, setDestText] = useState("");
  const [dest, setDest] = useState<PlaceRef | null>(null);
  const [departure, setDeparture] = useState(() => toLocalInputValue(nextFullHour()));
  const [loadText, setLoadText] = useState("42000");
  const [interval, setInterval] = useState("auto");
  const [errors, setErrors] = useState<string[]>([]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const problems: string[] = [];
    const load = Number(loadText.replace(/,/g, ""));
    const departureIso = fromLocalInput(departure);

    if (!originText.trim()) problems.push("Enter an origin.");
    if (!destText.trim()) problems.push("Enter a destination.");
    if (!departureIso) problems.push("Choose a departure date and time.");
    if (!Number.isFinite(load) || load < 0 || load > MAX_LOAD_LB || loadText.trim() === "") {
      problems.push(`Load weight must be between 0 and ${MAX_LOAD_LB.toLocaleString()} lb.`);
    }
    setErrors(problems);
    if (problems.length || !departureIso) return;

    onSubmit({
      // A picked suggestion carries exact coordinates; otherwise the server geocodes the text.
      origin: origin ?? originText.trim(),
      destination: dest ?? destText.trim(),
      departure: departureIso,
      load_lb: load,
      interval_miles: interval === "auto" ? null : (Number(interval) as 10 | 25 | 50),
    });
  }

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <PlaceInput
        label="Origin"
        placeholder="City or address"
        text={originText}
        selected={origin}
        onTextChange={(t) => {
          setOriginText(t);
          setOrigin(null);
        }}
        onSelect={(p) => {
          setOrigin(p);
          setOriginText(p.label);
        }}
      />
      <PlaceInput
        label="Destination"
        placeholder="City or address"
        text={destText}
        selected={dest}
        onTextChange={(t) => {
          setDestText(t);
          setDest(null);
        }}
        onSelect={(p) => {
          setDest(p);
          setDestText(p.label);
        }}
      />

      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input id="departure" type="datetime-local" value={departure} onChange={(e) => setDeparture(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="load">Load weight (lb)</label>
          <input
            id="load"
            type="text"
            inputMode="numeric"
            value={loadText}
            onChange={(e) => setLoadText(e.target.value)}
          />
        </div>
      </div>

      <div className="field">
        <label htmlFor="interval">Weather checkpoints</label>
        <select id="interval" value={interval} onChange={(e) => setInterval(e.target.value)}>
          <option value="auto">Automatic (by route length)</option>
          <option value="10">Every 10 miles</option>
          <option value="25">Every 25 miles</option>
          <option value="50">Every 50 miles</option>
        </select>
      </div>

      {errors.length > 0 && (
        <ul className="alert" role="alert">
          {errors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}

      <button type="submit" className="primary" disabled={loading}>
        {loading ? "Analyzing…" : "Find safest route"}
      </button>
    </form>
  );
}

export default memo(SearchForm);
