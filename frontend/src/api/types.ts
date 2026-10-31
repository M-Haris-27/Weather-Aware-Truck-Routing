/** Mirrors the JSON returned by the Django API (see backend/README.md). */

export type RiskName = "LOW" | "MODERATE" | "HIGH" | "SEVERE" | "NO_TRAVEL";

export interface PlaceRef {
  label: string;
  lat: number;
  lon: number;
}

export interface Checkpoint {
  index: number;
  lat: number;
  lon: number;
  mile: number;
  eta: string; // ISO 8601, UTC
  owned_miles: number;
  risk: RiskName;
  risk_level: number;
  wind_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
  reason: string;
}

export interface Route {
  id: string;
  summary: string;
  is_recommended: boolean;
  distance_mi: number;
  duration_min: number;
  arrival: string;
  miles_by_level: Record<RiskName, number>;
  avg_risk: number;
  worst_risk: RiskName;
  blocked: boolean;
  geometry: [number, number][]; // [lon, lat]
  checkpoints: Checkpoint[];
}

export interface HeatmapPoint {
  lat: number;
  lon: number;
  risk: number[]; // risk level 0-4 for each hour 0..hours after departure
}

export interface Heatmap {
  start: string;
  hours: number;
  spacing_miles: number;
  points: HeatmapPoint[];
}

export interface AnalysisResponse {
  recommended_route_id: string;
  recommendation_reason: string;
  all_routes_blocked: boolean;
  interval_miles: number;
  request: { origin: PlaceRef; destination: PlaceRef; departure: string; load_lb: number };
  routes: Route[];
  heatmap: Heatmap;
}

export interface AnalyzeRequest {
  origin: PlaceRef | string;
  destination: PlaceRef | string;
  departure: string; // ISO 8601
  load_lb: number;
  interval_miles?: 10 | 25 | 50 | null;
}
