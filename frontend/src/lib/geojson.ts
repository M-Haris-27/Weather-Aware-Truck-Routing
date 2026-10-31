import type { Feature, FeatureCollection, LineString, Point } from "geojson";
import type { Heatmap, Route } from "../api/types";

export const ROUTE_COLORS = ["#2563eb", "#7c3aed", "#0891b2"];

export function routeColor(index: number): string {
  return ROUTE_COLORS[index % ROUTE_COLORS.length];
}

export type RouteProps = { id: string; color: string; recommended: boolean };
export type CheckpointProps = {
  routeId: string;
  index: number;
  risk: string;
  riskLevel: number;
};
export type HeatProps = { risk: number };

export function routesGeoJSON(routes: Route[]): FeatureCollection<LineString, RouteProps> {
  return {
    type: "FeatureCollection",
    features: routes.map((route, i) => ({
      type: "Feature",
      properties: { id: route.id, color: routeColor(i), recommended: route.is_recommended },
      geometry: { type: "LineString", coordinates: route.geometry },
    })),
  };
}

export function checkpointsGeoJSON(routes: Route[]): FeatureCollection<Point, CheckpointProps> {
  return {
    type: "FeatureCollection",
    features: routes.flatMap((route) =>
      route.checkpoints.map(
        (cp): Feature<Point, CheckpointProps> => ({
          type: "Feature",
          properties: { routeId: route.id, index: cp.index, risk: cp.risk, riskLevel: cp.risk_level },
          geometry: { type: "Point", coordinates: [cp.lon, cp.lat] },
        }),
      ),
    ),
  };
}

/** One feature per heatmap point; `applyHour` then sets the property for the slider. */
export function heatmapFeatures(heatmap: Heatmap): Feature<Point, HeatProps>[] {
  return heatmap.points.map((p) => ({
    type: "Feature",
    properties: { risk: p.risk[0] ?? 0 },
    geometry: { type: "Point", coordinates: [p.lon, p.lat] },
  }));
}

/** Sets each feature's risk to its value for `hour` (clamped to the available hours). Mutates. */
export function applyHour(features: Feature<Point, HeatProps>[], heatmap: Heatmap, hour: number): void {
  const h = Math.max(0, Math.round(hour));
  features.forEach((feature, i) => {
    const series = heatmap.points[i].risk;
    feature.properties.risk = series[Math.min(h, series.length - 1)] ?? 0;
  });
}

export type Bounds = [[number, number], [number, number]]; // [[minLon, minLat], [maxLon, maxLat]]

export function boundsOf(coords: [number, number][]): Bounds | null {
  if (coords.length === 0) return null;
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  for (const [lon, lat] of coords) {
    if (lon < minLon) minLon = lon;
    if (lon > maxLon) maxLon = lon;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  }
  return [
    [minLon, minLat],
    [maxLon, maxLat],
  ];
}
