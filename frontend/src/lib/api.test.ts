import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, authStorage, request, resolveApiBase, setAuthFailureHandler } from "./api";
import type { AuthResponse } from "./types";

const fetchMock = vi.fn();

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const unauthorized = () => json(401, { error: { code: "unauthorized", message: "Token expired." } });

function authResp(access: string, refresh: string): AuthResponse {
  return {
    access_token: access,
    refresh_token: refresh,
    token_type: "bearer",
    user: { id: 1, name: "Alice", email: "alice@example.com", is_active: true, created_at: "2026-01-01T00:00:00Z" },
  };
}

const urlOf = (call: unknown[]) => String(call[0]);
const headersOf = (call: unknown[]) => ((call[1] as RequestInit | undefined)?.headers ?? {}) as Record<string, string>;
const refreshCalls = () => fetchMock.mock.calls.filter((c) => urlOf(c).endsWith("/auth/refresh"));

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  authStorage.clear();
  setAuthFailureHandler(null);
});

describe("basic requests", () => {
  it("sends the bearer token and parses JSON", async () => {
    authStorage.save(authResp("tok", "r1"));
    fetchMock.mockResolvedValueOnce(json(200, { hello: "world" }));

    await expect(request("/auth/me")).resolves.toEqual({ hello: "world" });
    expect(urlOf(fetchMock.mock.calls[0])).toBe("/api/auth/me");
    expect(headersOf(fetchMock.mock.calls[0]).Authorization).toBe("Bearer tok");
  });

  it("does not send a token when auth is disabled", async () => {
    authStorage.save(authResp("tok", "r1"));
    fetchMock.mockResolvedValueOnce(json(200, {}));
    await request("/auth/login", { method: "POST", body: { a: 1 }, auth: false });
    expect(headersOf(fetchMock.mock.calls[0]).Authorization).toBeUndefined();
  });

  it("returns null for 204 responses", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(request("/auth/logout", { method: "POST", body: {} })).resolves.toBeNull();
  });

  it("turns the server's error format into an ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      json(422, { error: { code: "validation_error", message: "Bad input", details: [{ field: "name", message: "required" }] } }),
    );
    const err = (await request("/projects", { method: "POST", body: {} }).catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 422, code: "validation_error", message: "Bad input" });
    expect(err.details).toEqual([{ field: "name", message: "required" }]);
  });

  it("copes with error responses that are not JSON", async () => {
    fetchMock.mockResolvedValueOnce(new Response("<html>Bad gateway</html>", { status: 502 }));
    await expect(request("/projects")).rejects.toMatchObject({ status: 502, code: "http_error", message: "Request failed (502)." });
  });

  it("reports network failures with status 0", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(request("/projects")).rejects.toMatchObject({ status: 0, code: "network_error" });
  });
});

describe("token refresh", () => {
  it("refreshes once on a 401 and retries with the new token", async () => {
    authStorage.save(authResp("old-access", "refresh-1"));
    fetchMock
      .mockResolvedValueOnce(unauthorized())                       // original request
      .mockResolvedValueOnce(json(200, authResp("new-access", "refresh-2"))) // refresh
      .mockResolvedValueOnce(json(200, { id: 1 }));                // retry

    await expect(request("/auth/me")).resolves.toEqual({ id: 1 });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(urlOf(fetchMock.mock.calls[1])).toBe("/api/auth/refresh");
    expect(JSON.parse((fetchMock.mock.calls[1][1] as RequestInit).body as string)).toEqual({ refresh_token: "refresh-1" });
    expect(headersOf(fetchMock.mock.calls[2]).Authorization).toBe("Bearer new-access");
    expect(localStorage.getItem("codescope.refresh_token")).toBe("refresh-2"); // rotated token stored
  });

  it("shares ONE refresh between concurrent requests (refresh tokens are single-use)", async () => {
    authStorage.save(authResp("old-access", "refresh-1"));
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) return json(200, authResp("new-access", "refresh-2"));
      const auth = (init?.headers as Record<string, string> | undefined)?.Authorization;
      return auth === "Bearer new-access" ? json(200, { ok: true }) : unauthorized();
    });

    const results = await Promise.all([request("/a"), request("/b"), request("/c")]);

    expect(results).toEqual([{ ok: true }, { ok: true }, { ok: true }]);
    expect(refreshCalls()).toHaveLength(1);
  });

  it("ends the session when the refresh token is rejected", async () => {
    authStorage.save(authResp("old", "refresh-1"));
    const onFailure = vi.fn();
    setAuthFailureHandler(onFailure);
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith("/auth/refresh") ? json(401, { error: { code: "unauthorized", message: "Refresh token is invalid." } }) : unauthorized(),
    );

    await expect(request("/auth/me")).rejects.toMatchObject({ status: 401 });

    expect(onFailure).toHaveBeenCalledTimes(1);
    expect(authStorage.hasRefreshToken()).toBe(false);
  });

  it("keeps the session when the server merely has a bad moment", async () => {
    authStorage.save(authResp("old", "refresh-1"));
    const onFailure = vi.fn();
    setAuthFailureHandler(onFailure);
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith("/auth/refresh") ? json(500, {}) : unauthorized(),
    );

    await expect(request("/auth/me")).rejects.toMatchObject({ status: 401 });

    expect(onFailure).not.toHaveBeenCalled();
    expect(authStorage.hasRefreshToken()).toBe(true); // a 5xx must not log people out
  });
});


describe("resolveApiBase", () => {
  it.each([
    [undefined, "/api"],
    ["", "/api"],
    ["   ", "/api"],
    ["/api", "/api"],
    ["https://codescope-api.onrender.com/api", "https://codescope-api.onrender.com/api"],
    ["https://codescope-api.onrender.com", "https://codescope-api.onrender.com/api"], // forgot /api
    ["https://codescope-api.onrender.com/", "https://codescope-api.onrender.com/api"], // trailing slash
    ["https://codescope-api.onrender.com/api/", "https://codescope-api.onrender.com/api"],
    ["http://localhost:8000", "http://localhost:8000/api"],
  ])("%j -> %s", (raw, expected) => {
    expect(resolveApiBase(raw)).toBe(expected);
  });
});
