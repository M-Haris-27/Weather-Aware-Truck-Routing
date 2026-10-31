import { describe, expect, it } from "vitest";
import type { Heatmap, Route } from "../api/types";
import { applyHour, boundsOf, checkpointsGeoJSON, heatmapFeatures, routeColor, routesGeoJSON } from "./geojson";

const route = (id: string, recommended = false): Route => ({
  id,
  summary: id,
  is_recommended: recommended,
  distance_mi: 100,
  duration_min: 90,
  arrival: "2026-11-05T14:00:00Z",
  miles_by_level: { LOW: 100, MODERATE: 0, HIGH: 0, SEVERE: 0, NO_TRAVEL: 0 },
  avg_risk: 0,
  worst_risk: "LOW",
  blocked: false,
  geometry: [
    [-100, 35],
    [-99, 36],
  ],
  checkpoints: [
    { index: 0, lat: 35, lon: -100, mile: 0, eta: "2026-11-05T12:00:00Z", owned_miles: 50, risk: "LOW", risk_level: 0, wind_mph: 10, rain_in_hr: 0, snow_in_hr: 0, reason: "ok" },
    { index: 1, lat: 36, lon: -99, mile: 100, eta: "2026-11-05T13:30:00Z", owned_miles: 50, risk: "HIGH", risk_level: 2, wind_mph: 40, rain_in_hr: 0, snow_in_hr: 0, reason: "wind" },
  ],
});

const heatmap: Heatmap = {
  start: "2026-11-05T12:00:00Z",
  hours: 3,
  spacing_miles: 25,
  points: [
    { lat: 35, lon: -100, risk: [0, 1, 2, 4] },
    { lat: 36, lon: -99, risk: [3, 3, 0, 0] },
  ],
};

describe("routesGeoJSON", () => {
  it("builds one LineString per route with a stable color per index", () => {
    const fc = routesGeoJSON([route("a", true), route("b")]);
    expect(fc.features).toHaveLength(2);
    expect(fc.features[0].properties).toEqual({ id: "a", color: routeColor(0), recommended: true });
    expect(fc.features[1].geometry.coordinates).toEqual([
      [-100, 35],
      [-99, 36],
    ]);
    expect(routeColor(0)).not.toBe(routeColor(1));
  });
});

describe("checkpointsGeoJSON", () => {
  it("flattens checkpoints across routes in [lon, lat] order", () => {
    const fc = checkpointsGeoJSON([route("a"), route("b")]);
    expect(fc.features).toHaveLength(4);
    expect(fc.features[1].geometry.coordinates).toEqual([-99, 36]);
    expect(fc.features[1].properties).toMatchObject({ routeId: "a", index: 1, risk: "HIGH", riskLevel: 2 });
  });
});

describe("heatmap features", () => {
  it("starts at hour 0 and updates in place when the hour changes", () => {
    const features = heatmapFeatures(heatmap);
    expect(features.map((f) => f.properties.risk)).toEqual([0, 3]);

    applyHour(features, heatmap, 3);
    expect(features.map((f) => f.properties.risk)).toEqual([4, 0]);

    applyHour(features, heatmap, 1);
    expect(features.map((f) => f.properties.risk)).toEqual([1, 3]);
  });

  it("clamps hours beyond the available data and negative hours", () => {
    const features = heatmapFeatures(heatmap);
    applyHour(features, heatmap, 99);
    expect(features.map((f) => f.properties.risk)).toEqual([4, 0]);
    applyHour(features, heatmap, -4);
    expect(features.map((f) => f.properties.risk)).toEqual([0, 3]);
  });
});

describe("boundsOf", () => {
  it("returns the bounding box, or null for no coordinates", () => {
    expect(
      boundsOf([
        [-100, 35],
        [-90, 40],
        [-95, 30],
      ]),
    ).toEqual([
      [-100, 30],
      [-90, 40],
    ]);
    expect(boundsOf([])).toBeNull();
  });
});
