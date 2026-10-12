import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../lib/api";
import LoginPage from "./LoginPage";

const login = vi.hoisted(() => vi.fn());
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ login, status: "anonymous", user: null }) }));

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<p>Dashboard page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  login.mockReset();
});

describe("LoginPage", () => {
  it("keeps the submit button disabled until both fields are filled", async () => {
    const user = userEvent.setup();
    renderPage();
    const submit = screen.getByRole("button", { name: "Sign in" });
    expect(submit).toBeDisabled();

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    expect(submit).toBeDisabled();
    await user.type(screen.getByLabelText("Password"), "Secret123");
    expect(submit).toBeEnabled();
  });

  it("signs in and goes to the dashboard", async () => {
    login.mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "Secret123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Dashboard page")).toBeInTheDocument();
    expect(login).toHaveBeenCalledWith("alice@example.com", "Secret123");
  });

  it("shows the server's message when credentials are wrong", async () => {
    login.mockRejectedValue(new ApiError(401, "unauthorized", "Invalid email or password."));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(screen.queryByText("Dashboard page")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled(); // can try again
  });

  it("lets people reveal and hide the password", async () => {
    const user = userEvent.setup();
    renderPage();
    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute("type", "password");

    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(input).toHaveAttribute("type", "text");
    await user.click(screen.getByRole("button", { name: "Hide password" }));
    expect(input).toHaveAttribute("type", "password");
  });
});
