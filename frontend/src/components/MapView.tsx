import maplibregl from "maplibre-gl";
import type { ExpressionSpecification, FilterSpecification, GeoJSONSource, Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { FeatureCollection } from "geojson";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { AnalysisResponse, PlaceRef } from "../api/types";
import { routeTitle } from "../lib/format";
import {
  applyHour,
  boundsOf,
  checkpointsGeoJSON,
  heatmapFeatures,
  routesGeoJSON,
} from "../lib/geojson";
import { buildCheckpointPopup } from "../lib/popup";
import { RISK_COLORS } from "../lib/risk";

const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

const ROUTE_LAYERS = ["routes-selected", "routes"];
const CHECKPOINT_LAYERS = ["checkpoints-selected", "checkpoints"];

const RISK_COLOR_EXPR: ExpressionSpecification = [
  "match",
  ["get", "risk"],
  "LOW",
  RISK_COLORS.LOW,
  "MODERATE",
  RISK_COLORS.MODERATE,
  "HIGH",
  RISK_COLORS.HIGH,
  "SEVERE",
  RISK_COLORS.SEVERE,
  "NO_TRAVEL",
  RISK_COLORS.NO_TRAVEL,
  "#94a3b8",
];

export interface FocusRequest {
  routeId: string;
  index: number;
  nonce: number; // changes on every request so clicking the same row twice works
}

interface Props {
  result: AnalysisResponse | null;
  selectedRouteId: string | null;
  onSelectRoute: (id: string) => void;
  showHeatmap: boolean;
  hour: number;
  focus: FocusRequest | null;
}

const idFilter = (id: string | null): FilterSpecification => ["==", ["get", "id"], id ?? ""];
const routeFilter = (id: string | null): FilterSpecification => ["==", ["get", "routeId"], id ?? ""];

/** Sources and layers. Heatmap and route lines sit below the basemap's labels. */
function addLayers(map: MapLibreMap) {
  const beforeLabels = map.getStyle().layers.find((layer) => layer.type === "symbol")?.id;
  map.addSource("heat", { type: "geojson", data: EMPTY });
  map.addSource("routes", { type: "geojson", data: EMPTY });
  map.addSource("checkpoints", { type: "geojson", data: EMPTY });

  map.addLayer(
    {
      id: "heat",
      type: "heatmap",
      source: "heat",
      layout: { visibility: "none" },
      paint: {
        "heatmap-weight": ["interpolate", ["linear"], ["get", "risk"], 0, 0, 1, 0.3, 2, 0.55, 3, 0.85, 4, 1],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 3, 0.6, 8, 1.2],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 3, 18, 6, 40, 9, 90, 12, 180],
        "heatmap-opacity": 0.85,
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(0,0,0,0)",
          0.15,
          "rgba(250,204,21,0.45)",
          0.4,
          "rgba(249,115,22,0.65)",
          0.7,
          "rgba(220,38,38,0.78)",
          1,
          "rgba(127,29,29,0.9)",
        ],
      },
    },
    beforeLabels,
  );

  const line = { "line-cap": "round", "line-join": "round" } as const;
  // All routes, dimmed.
  map.addLayer(
    {
      id: "routes-casing",
      type: "line",
      source: "routes",
      layout: line,
      paint: { "line-color": "#ffffff", "line-width": 6, "line-opacity": 0.6 },
    },
    beforeLabels,
  );
  map.addLayer(
    {
      id: "routes",
      type: "line",
      source: "routes",
      layout: line,
      paint: { "line-color": ["get", "color"], "line-width": 3.5, "line-opacity": 0.55 },
    },
    beforeLabels,
  );
  // The selected route is drawn again on top. Changing selection only swaps a filter,
  // so the route geometry is never re-tiled.
  map.addLayer(
    {
      id: "routes-selected-casing",
      type: "line",
      source: "routes",
      filter: idFilter(null),
      layout: line,
      paint: { "line-color": "#ffffff", "line-width": 9, "line-opacity": 0.9 },
    },
    beforeLabels,
  );
  map.addLayer(
    {
      id: "routes-selected",
      type: "line",
      source: "routes",
      filter: idFilter(null),
      layout: line,
      paint: { "line-color": ["get", "color"], "line-width": 5.5, "line-opacity": 1 },
    },
    beforeLabels,
  );

  map.addLayer({
    id: "checkpoints",
    type: "circle",
    source: "checkpoints",
    paint: {
      "circle-radius": 3.5,
      "circle-color": RISK_COLOR_EXPR,
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 1,
      "circle-opacity": 0.7,
    },
  });
  map.addLayer({
    id: "checkpoints-selected",
    type: "circle",
    source: "checkpoints",
    filter: routeFilter(null),
    paint: {
      "circle-radius": 6.5,
      "circle-color": RISK_COLOR_EXPR,
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2,
    },
  });
}

function endpointMarker(place: PlaceRef, letter: string, map: MapLibreMap): maplibregl.Marker {
  const element = document.createElement("div");
  element.className = "endpoint";
  element.textContent = letter;
  element.title = place.label;
  return new maplibregl.Marker({ element }).setLngLat([place.lon, place.lat]).addTo(map);
}

export default function MapView({ result, selectedRouteId, onSelectRoute, showHeatmap, hour, focus }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const fittedRef = useRef<{ result: AnalysisResponse | null; selected: string | null }>({ result: null, selected: null });
  const [ready, setReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  // Event handlers registered once need the latest props, so read them through refs.
  const resultRef = useRef(result);
  resultRef.current = result;
  const onSelectRef = useRef(onSelectRoute);
  onSelectRef.current = onSelectRoute;

  const openPopup = useCallback((routeId: string, index: number) => {
    const map = mapRef.current;
    const current = resultRef.current;
    if (!map || !current) return;
    const routeIndex = current.routes.findIndex((r) => r.id === routeId);
    const cp = current.routes[routeIndex]?.checkpoints[index];
    if (!cp) return;
    popupRef.current?.remove();
    popupRef.current = new maplibregl.Popup({ offset: 12, maxWidth: "260px" })
      .setLngLat([cp.lon, cp.lat])
      .setDOMContent(buildCheckpointPopup(cp, routeTitle(current.routes[routeIndex].summary, routeIndex)))
      .addTo(map);
  }, []);

  // --- create the map once -----------------------------------------------------------
  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center: [-98.5, 39.5],
      zoom: 3.6,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

    let loaded = false;
    map.on("error", () => {
      if (!loaded) setMapError("Couldn't load the map. Check your internet connection and reload.");
    });

    map.on("load", () => {
      loaded = true;
      addLayers(map);
      mapRef.current = map;
      setMapError(null);
      setReady(true);
    });

    map.on("click", (event) => {
      const pad = 6;
      const box: [[number, number], [number, number]] = [
        [event.point.x - pad, event.point.y - pad],
        [event.point.x + pad, event.point.y + pad],
      ];
      const checkpoint = map.queryRenderedFeatures(box, { layers: CHECKPOINT_LAYERS })[0];
      if (checkpoint) {
        const { routeId, index } = checkpoint.properties as { routeId: string; index: number };
        openPopup(routeId, index);
        return;
      }
      const route = map.queryRenderedFeatures(box, { layers: ROUTE_LAYERS })[0];
      if (route) onSelectRef.current((route.properties as { id: string }).id);
    });

    map.on("mousemove", (event) => {
      if (!map.getLayer("routes")) return;
      const hit = map.queryRenderedFeatures(event.point, { layers: [...CHECKPOINT_LAYERS, ...ROUTE_LAYERS] });
      map.getCanvas().style.cursor = hit.length ? "pointer" : "";
    });

    return () => {
      popupRef.current?.remove();
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
  }, [openPopup]);

  // --- routes, checkpoints, A/B markers (once per result) -----------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    (map.getSource("routes") as GeoJSONSource).setData(result ? routesGeoJSON(result.routes) : EMPTY);
    (map.getSource("checkpoints") as GeoJSONSource).setData(result ? checkpointsGeoJSON(result.routes) : EMPTY);
    popupRef.current?.remove();
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = result
      ? [endpointMarker(result.request.origin, "A", map), endpointMarker(result.request.destination, "B", map)]
      : [];
  }, [ready, result]);

  // --- selection: just swap filters --------------------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    map.setFilter("routes-selected", idFilter(selectedRouteId));
    map.setFilter("routes-selected-casing", idFilter(selectedRouteId));
    map.setFilter("checkpoints-selected", routeFilter(selectedRouteId));
  }, [ready, selectedRouteId]);

  // --- camera: frame all routes for a new result, or the chosen route on selection ----
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !result) return;
    const resultChanged = fittedRef.current.result !== result;
    if (!resultChanged && fittedRef.current.selected === selectedRouteId) return;
    fittedRef.current = { result, selected: selectedRouteId };

    const chosen = resultChanged ? undefined : result.routes.find((r) => r.id === selectedRouteId);
    const bounds = boundsOf(chosen ? chosen.geometry : result.routes.flatMap((r) => r.geometry));
    if (bounds) {
      map.fitBounds(bounds, { padding: { top: 70, right: 60, bottom: 140, left: 60 }, duration: 900, maxZoom: 12 });
    }
  }, [ready, result, selectedRouteId]);

  // --- heatmap -----------------------------------------------------------------------
  const heatFeatures = useMemo(() => (result ? heatmapFeatures(result.heatmap) : []), [result]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    map.setLayoutProperty("heat", "visibility", showHeatmap && result ? "visible" : "none");
  }, [ready, showHeatmap, result]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !result || !showHeatmap) return;
    // One update per animation frame: dragging the slider never queues redundant work,
    // and no network request is involved (all 49 hours arrived with the result).
    const frame = requestAnimationFrame(() => {
      applyHour(heatFeatures, result.heatmap, hour);
      (map.getSource("heat") as GeoJSONSource).setData({ type: "FeatureCollection", features: heatFeatures });
    });
    return () => cancelAnimationFrame(frame);
  }, [ready, result, showHeatmap, hour, heatFeatures]);

  // --- "show on map" from the checkpoint table ----------------------------------------
  useEffect(() => {
    const map = mapRef.current;
    const current = resultRef.current;
    if (!focus || !ready || !map || !current) return;
    const cp = current.routes.find((r) => r.id === focus.routeId)?.checkpoints[focus.index];
    if (!cp) return;
    map.easeTo({ center: [cp.lon, cp.lat], zoom: Math.max(map.getZoom(), 8), duration: 600 });
    openPopup(focus.routeId, focus.index);
  }, [focus, ready, openPopup]);

  return (
    <>
      <div ref={containerRef} className="map" />
      {mapError && (
        <div className="map-error" role="alert">
          {mapError}
        </div>
      )}
    </>
  );
}
