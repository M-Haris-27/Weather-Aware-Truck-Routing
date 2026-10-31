import { describe, expect, it } from "vitest";
import { describeError } from "./client";

describe("describeError", () => {
  it("uses the API's error message", () => {
    expect(describeError({ error: "No drivable route found" }, "fallback")).toBe("No drivable route found");
  });

  it("flattens per-field validation details into one sentence", () => {
    const body = { error: "Invalid request", details: { load_lb: ["Ensure this value is greater than or equal to 0."], origin: ["Required."] } };
    expect(describeError(body, "fallback")).toBe(
      "load lb: Ensure this value is greater than or equal to 0. · origin: Required.",
    );
  });

  it("falls back when the body is unusable", () => {
    expect(describeError(null, "fallback")).toBe("fallback");
    expect(describeError("oops", "fallback")).toBe("fallback");
  });
});
