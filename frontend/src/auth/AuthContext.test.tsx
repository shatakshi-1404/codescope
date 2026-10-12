import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authStorage, setAuthFailureHandler } from "../lib/api";
import type { AuthResponse } from "../lib/types";
import { AuthProvider, useAuth } from "./AuthContext";

const fetchMock = vi.fn();
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const session = (refresh: string): AuthResponse => ({
  access_token: "access",
  refresh_token: refresh,
  token_type: "bearer",
  user: { id: 1, name: "Alice", email: "alice@example.com", is_active: true, created_at: "2026-01-01T00:00:00Z" },
});

function Probe() {
  const { status, user, logout } = useAuth();
  return (
    <div>
      <p data-testid="status">{status}</p>
      <p data-testid="user">{user?.name ?? "nobody"}</p>
      <button onClick={() => void logout()}>Sign out</button>
    </div>
  );
}

function renderApp() {
  return render(
    <StrictMode>
      <QueryClientProvider client={new QueryClient()}>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
}

const refreshCalls = () => fetchMock.mock.calls.filter((c) => String(c[0]).endsWith("/auth/refresh"));

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  authStorage.clear();
  setAuthFailureHandler(null);
});

describe("AuthProvider", () => {
  it("is anonymous without a stored session and makes no requests", async () => {
    renderApp();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("restores the session on page load, with exactly one refresh even under StrictMode", async () => {
    localStorage.setItem("codescope.refresh_token", "r1");
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith("/auth/refresh") ? json(200, session("r2")) : json(500, {}),
    );

    renderApp();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("user")).toHaveTextContent("Alice");
    expect(refreshCalls()).toHaveLength(1);
    expect(localStorage.getItem("codescope.refresh_token")).toBe("r2");
  });

  it("falls back to anonymous when the stored session is no longer valid", async () => {
    localStorage.setItem("codescope.refresh_token", "stale");
    fetchMock.mockResolvedValue(json(401, { error: { code: "unauthorized", message: "Refresh token is invalid or expired." } }));

    renderApp();

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
    expect(localStorage.getItem("codescope.refresh_token")).toBeNull();
  });

  it("logging out clears local state and revokes the token on the server", async () => {
    localStorage.setItem("codescope.refresh_token", "r1");
    fetchMock.mockImplementation(async (url: string) =>
      url.endsWith("/auth/refresh") ? json(200, session("r2")) : new Response(null, { status: 204 }),
    );
    const user = userEvent.setup();
    renderApp();
    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
    expect(screen.getByTestId("user")).toHaveTextContent("nobody");
    expect(localStorage.getItem("codescope.refresh_token")).toBeNull();

    const logout = fetchMock.mock.calls.find((c) => String(c[0]).endsWith("/auth/logout"));
    expect(logout).toBeDefined();
    expect(JSON.parse((logout![1] as RequestInit).body as string)).toEqual({ refresh_token: "r2" });
  });
});
