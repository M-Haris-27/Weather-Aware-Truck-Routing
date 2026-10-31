import { useMutation } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { analyze } from "./api/client";
import type { AnalysisResponse, AnalyzeRequest } from "./api/types";
import CheckpointTable from "./components/CheckpointTable";
import HeatmapControl from "./components/HeatmapControl";
import Legend from "./components/Legend";
import MapView, { type FocusRequest } from "./components/MapView";
import RouteCards from "./components/RouteCards";
import SearchForm from "./components/SearchForm";
import { formatDateTime, routeTitle } from "./lib/format";

export default function App() {
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [hour, setHour] = useState(0);
  const [focus, setFocus] = useState<FocusRequest | null>(null);

  const mutation = useMutation({
    mutationFn: (request: AnalyzeRequest) => analyze(request),
    onSuccess: (data) => {
      setResult(data);
      setSelectedId(data.recommended_route_id);
      setHour(0);
      setFocus(null);
    },
  });

  const submit = mutation.mutate;
  const handleSubmit = useCallback((request: AnalyzeRequest) => submit(request), [submit]);
  const handleFocus = useCallback(
    (routeId: string, index: number) => setFocus((prev) => ({ routeId, index, nonce: (prev?.nonce ?? 0) + 1 })),
    [],
  );

  const selectedIndex = result ? result.routes.findIndex((r) => r.id === selectedId) : -1;
  const selectedRoute = selectedIndex >= 0 && result ? result.routes[selectedIndex] : null;

  return (
    <div className="app">
      <aside className="sidebar">
        <header className="brand">
          <h1>Weather-Aware Truck Routing</h1>
          <p>Compare routes by weather risk, load weight and travel time.</p>
        </header>

        <SearchForm loading={mutation.isPending} onSubmit={handleSubmit} />

        {mutation.isError && (
          <div className="alert" role="alert">
            {mutation.error.message}
          </div>
        )}

        {result ? (
          <>
            <p className="trip">
              {result.request.origin.label || "Origin"} → {result.request.destination.label || "Destination"} · departs{" "}
              {formatDateTime(result.request.departure)} · {result.request.load_lb.toLocaleString()} lb · checkpoints every{" "}
              {result.interval_miles} mi
            </p>
            <RouteCards
              routes={result.routes}
              selectedId={selectedId}
              recommendedId={result.recommended_route_id}
              reason={result.recommendation_reason}
              allBlocked={result.all_routes_blocked}
              onSelect={setSelectedId}
            />
            {selectedRoute && (
              <CheckpointTable
                route={selectedRoute}
                title={routeTitle(selectedRoute.summary, selectedIndex)}
                onFocus={handleFocus}
              />
            )}
          </>
        ) : (
          !mutation.isPending && (
            <p className="hint">Enter a trip above to compare up to three routes and see the weather along each.</p>
          )
        )}
      </aside>

      <main className="map-wrap">
        <MapView
          result={result}
          selectedRouteId={selectedId}
          onSelectRoute={setSelectedId}
          showHeatmap={showHeatmap}
          hour={hour}
          focus={focus}
        />
        <Legend />
        {result && (
          <HeatmapControl
            enabled={showHeatmap}
            onToggle={setShowHeatmap}
            hour={hour}
            maxHour={result.heatmap.hours}
            onHourChange={setHour}
            start={result.heatmap.start}
          />
        )}
        {mutation.isPending && (
          <div className="overlay" role="status">
            <span className="spinner" /> Analyzing routes and weather…
          </div>
        )}
      </main>
    </div>
  );
}
