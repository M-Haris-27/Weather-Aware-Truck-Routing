export function formatDuration(totalMinutes: number): string {
  const minutes = Math.max(0, Math.round(totalMinutes));
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`;
}

export function formatMiles(miles: number): string {
  return `${miles >= 100 ? Math.round(miles).toLocaleString() : miles.toFixed(1)} mi`;
}

export function formatDateTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

/** Compact form for tables: "Fri 10:00 PM". */
export function formatShortDateTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" }).format(date);
}

export function addHours(iso: string, hours: number): Date {
  return new Date(new Date(iso).getTime() + hours * 3_600_000);
}

const pad = (n: number) => String(n).padStart(2, "0");

/** Date -> value for <input type="datetime-local"> in the browser's local time. */
export function toLocalInputValue(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** <input type="datetime-local"> value (local time) -> ISO 8601 in UTC. Null if invalid. */
export function fromLocalInput(value: string): string | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

/** The next full hour from `now`, a sensible default departure. */
export function nextFullHour(now = new Date()): Date {
  const next = new Date(now);
  next.setMinutes(0, 0, 0);
  next.setHours(next.getHours() + 1);
  return next;
}

/** "Route 2 · I-35 N", or just "Route 2" when the provider gave no road names. */
export function routeTitle(summary: string, index: number): string {
  return /^Route \d+$/i.test(summary) ? `Route ${index + 1}` : `Route ${index + 1} · ${summary}`;
}
