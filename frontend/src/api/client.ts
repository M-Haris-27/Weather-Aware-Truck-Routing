import type { AnalysisResponse, AnalyzeRequest, PlaceRef } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Turns the API's {"error", "details"} body into one readable sentence. */
export function describeError(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const { error, details } = body as { error?: string; details?: Record<string, unknown> };
  if (details && typeof details === "object") {
    const parts = Object.entries(details).map(([field, msgs]) => {
      const text = Array.isArray(msgs) ? msgs.join(" ") : JSON.stringify(msgs);
      return `${field.replace(/_/g, " ")}: ${text}`;
    });
    if (parts.length) return parts.join(" · ");
  }
  return error || fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, init);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError("Can't reach the server. Is the backend running?", 0);
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(describeError(body, `Request failed (HTTP ${response.status})`), response.status);
  }
  return body as T;
}

export function analyze(payload: AnalyzeRequest, signal?: AbortSignal): Promise<AnalysisResponse> {
  return request<AnalysisResponse>("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export async function geocode(query: string, signal?: AbortSignal): Promise<PlaceRef[]> {
  const data = await request<{ results: PlaceRef[] }>(`/api/geocode?q=${encodeURIComponent(query)}`, { signal });
  return data.results;
}
