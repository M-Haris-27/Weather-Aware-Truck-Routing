import { describe, expect, it } from "vitest";
import {
  addHours,
  formatDuration,
  formatMiles,
  formatShortDateTime,
  fromLocalInput,
  nextFullHour,
  routeTitle,
  toLocalInputValue,
} from "./format";

describe("formatDuration", () => {
  it("formats minutes and hours", () => {
    expect(formatDuration(0)).toBe("0m");
    expect(formatDuration(59)).toBe("59m");
    expect(formatDuration(60)).toBe("1h 00m");
    expect(formatDuration(440)).toBe("7h 20m");
    expect(formatDuration(-5)).toBe("0m");
  });
});

describe("formatMiles", () => {
  it("uses one decimal below 100 miles and whole miles above", () => {
    expect(formatMiles(12.34)).toBe("12.3 mi");
    expect(formatMiles(453.4)).toBe("453 mi");
  });
});

describe("local datetime helpers", () => {
  it("round-trips a local time through the datetime-local format", () => {
    const local = new Date(2026, 10, 5, 14, 5); // 5 Nov 2026 14:05 local
    const value = toLocalInputValue(local);
    expect(value).toBe("2026-11-05T14:05");
    expect(new Date(fromLocalInput(value)!).getTime()).toBe(local.getTime());
  });

  it("returns null for an empty or invalid value", () => {
    expect(fromLocalInput("")).toBeNull();
    expect(fromLocalInput("nope")).toBeNull();
  });

  it("nextFullHour rounds up to the following hour", () => {
    const next = nextFullHour(new Date(2026, 10, 5, 14, 20, 30));
    expect([next.getHours(), next.getMinutes(), next.getSeconds()]).toEqual([15, 0, 0]);
    expect(nextFullHour(new Date(2026, 10, 5, 23, 59)).getDate()).toBe(6);
  });

  it("addHours offsets an ISO timestamp", () => {
    expect(addHours("2026-11-05T12:00:00Z", 6).toISOString()).toBe("2026-11-05T18:00:00.000Z");
  });
});

describe("routeTitle", () => {
  it("avoids repeating generic names and includes road summaries", () => {
    expect(routeTitle("Route 2", 1)).toBe("Route 2");
    expect(routeTitle("I-35 N", 0)).toBe("Route 1 · I-35 N");
  });
});

describe("formatShortDateTime", () => {
  it("includes the weekday and the time", () => {
    const text = formatShortDateTime(new Date(2026, 10, 6, 22, 0)); // Fri 6 Nov 2026, 10 PM local
    expect(text).toMatch(/Fri/);
    expect(text).toMatch(/10:00/);
  });
});
