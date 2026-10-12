import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { GuestRoute, ProtectedRoute } from "./RouteGuards";

const auth = vi.hoisted(() => ({ status: "loading" as "loading" | "anonymous" | "authenticated" }));
vi.mock("./AuthContext", () => ({ useAuth: () => ({ status: auth.status }) }));

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<p>Login page</p>} />
        <Route element={<GuestRoute />}>
          <Route path="/register" element={<p>Register page</p>} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<p>Secret dashboard</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("sends anonymous visitors to the login page", () => {
    auth.status = "anonymous";
    renderAt("/dashboard");
    expect(screen.getByText("Login page")).toBeInTheDocument();
    expect(screen.queryByText("Secret dashboard")).not.toBeInTheDocument();
  });

  it("shows the page to authenticated users", () => {
    auth.status = "authenticated";
    renderAt("/dashboard");
    expect(screen.getByText("Secret dashboard")).toBeInTheDocument();
  });

  it("shows a loader (never the page, never a redirect) while the session is being restored", () => {
    auth.status = "loading";
    renderAt("/dashboard");
    expect(screen.getByRole("status")).toHaveTextContent("Loading CodeScope");
    expect(screen.queryByText("Secret dashboard")).not.toBeInTheDocument();
    expect(screen.queryByText("Login page")).not.toBeInTheDocument();
  });
});

describe("GuestRoute", () => {
  it("lets anonymous visitors see the register page", () => {
    auth.status = "anonymous";
    renderAt("/register");
    expect(screen.getByText("Register page")).toBeInTheDocument();
  });

  it("sends signed-in users to the dashboard", () => {
    auth.status = "authenticated";
    renderAt("/register");
    expect(screen.getByText("Secret dashboard")).toBeInTheDocument();
  });
});
