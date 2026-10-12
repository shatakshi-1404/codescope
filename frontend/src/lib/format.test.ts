import { beforeEach, describe, expect, it, vi } from "vitest";

import { isActive, scoreLabel, scoreTone, shortSha, timeAgo } from "./format";

describe("timeAgo", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-03T12:00:00Z"));
  });

  it.each([
    ["2026-10-03T11:59:50Z", "just now"],
    ["2026-10-03T11:50:00Z", "10 min ago"],
    ["2026-10-03T09:00:00Z", "3 h ago"],
    ["2026-10-01T12:00:00Z", "2 d ago"],
  ])("%s -> %s", (iso, expected) => {
    expect(timeAgo(iso)).toBe(expected);
  });

  it("switches to a calendar date after a week", () => {
    expect(timeAgo("2026-08-01T12:00:00Z")).not.toMatch(/ago|just now/);
  });
});

describe("scores", () => {
  it.each([
    [95, "Excellent"],
    [90, "Excellent"],
    [85, "Good"],
    [70, "Fair"],
    [55, "Needs attention"],
    [10, "Poor"],
  ])("scoreLabel(%i) = %s", (score, label) => {
    expect(scoreLabel(score)).toBe(label);
  });

  it("colours scores by band", () => {
    expect(scoreTone(80)).toContain("brand");
    expect(scoreTone(70)).toContain("amber");
    expect(scoreTone(40)).toContain("red");
  });
});

describe("small helpers", () => {
  it("shortens commit hashes", () => {
    expect(shortSha("0123456789abcdef")).toBe("0123456");
    expect(shortSha(null)).toBe("—");
  });

  it("knows which analysis states are still running", () => {
    expect(isActive("PENDING")).toBe(true);
    expect(isActive("RUNNING")).toBe(true);
    expect(isActive("COMPLETED")).toBe(false);
    expect(isActive("FAILED")).toBe(false);
    expect(isActive(undefined)).toBe(false);
  });
});
