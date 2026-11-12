import { describe, expect, it } from "vitest";
import { clamp, formatCount, gradeTone, quickRepoCheck, timeAgo } from "@/lib/format";

describe("timeAgo", () => {
  const now = new Date("2026-11-12T12:00:00Z");

  it("returns 'unknown' for missing or invalid dates", () => {
    expect(timeAgo(null, now)).toBe("unknown");
    expect(timeAgo("not-a-date", now)).toBe("unknown");
  });

  it("says 'just now' for very recent times", () => {
    expect(timeAgo("2026-11-12T11:59:30Z", now)).toBe("just now");
  });

  it("uses relative units for older times", () => {
    expect(timeAgo("2026-11-11T12:00:00Z", now)).toBe("yesterday");
    expect(timeAgo("2026-11-05T12:00:00Z", now)).toBe("last week");
    expect(timeAgo("2026-11-12T10:00:00Z", now)).toBe("2 hours ago");
  });
});

describe("formatCount", () => {
  it("abbreviates large numbers", () => {
    expect(formatCount(1200)).toBe("1.2K");
    expect(formatCount(42)).toBe("42");
  });
});

describe("clamp", () => {
  it("keeps values in range", () => {
    expect(clamp(-5, 0, 10)).toBe(0);
    expect(clamp(50, 0, 10)).toBe(10);
    expect(clamp(5, 0, 10)).toBe(5);
  });
});

describe("quickRepoCheck", () => {
  it("rejects empty input and whitespace inside references", () => {
    expect(quickRepoCheck("   ")).toMatch(/Enter/);
    expect(quickRepoCheck("owner/repo name")).toMatch(/spaces/);
  });

  it("lets plausible input through to the server", () => {
    expect(quickRepoCheck("octocat/Hello-World")).toBeNull();
    expect(quickRepoCheck("https://github.com/octocat/Hello-World")).toBeNull();
  });
});

describe("gradeTone", () => {
  it("maps scores to colour tones", () => {
    expect(gradeTone(95)).toBe("emerald");
    expect(gradeTone(72)).toBe("cyan");
    expect(gradeTone(55)).toBe("amber");
    expect(gradeTone(10)).toBe("rose");
  });
});
