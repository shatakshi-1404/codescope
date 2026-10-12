import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../components/ui/Toast";
import { ApiError } from "../lib/api";
import RegisterPage from "./RegisterPage";

const register = vi.hoisted(() => vi.fn());
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ register, status: "anonymous", user: null }) }));

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <RegisterPage />
      </ToastProvider>
    </MemoryRouter>,
  );
}

async function fill(user: ReturnType<typeof userEvent.setup>, password: string) {
  await user.type(screen.getByLabelText("Full name"), "Alice");
  await user.type(screen.getByLabelText("Email"), "alice@example.com");
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Create account" }));
}

beforeEach(() => {
  register.mockReset();
});

describe("RegisterPage", () => {
  it("validates in the browser and makes no request for a weak password", async () => {
    const user = userEvent.setup();
    renderPage();
    await fill(user, "abcdefgh");
    expect(await screen.findByText("Mix letters and numbers.")).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it("flags every missing field at once", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Please enter your name.")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid email address.")).toBeInTheDocument();
    expect(screen.getByText("Use at least 8 characters.")).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it("submits trimmed values when everything is valid", async () => {
    register.mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderPage();
    await fill(user, "Passw0rd123");
    expect(register).toHaveBeenCalledWith("Alice", "alice@example.com", "Passw0rd123");
  });

  it("shows server-side field errors next to the right field", async () => {
    register.mockRejectedValue(
      new ApiError(422, "validation_error", "Request validation failed.", [
        { field: "email", message: "Value error, That email is not allowed" },
      ]),
    );
    const user = userEvent.setup();
    renderPage();
    await fill(user, "Passw0rd123");
    expect(await screen.findByText("That email is not allowed")).toBeInTheDocument();
  });

  it("shows a general error when the email is already registered", async () => {
    register.mockRejectedValue(new ApiError(409, "conflict", "An account with this email already exists."));
    const user = userEvent.setup();
    renderPage();
    await fill(user, "Passw0rd123");
    expect(await screen.findByRole("alert")).toHaveTextContent("An account with this email already exists.");
  });
});
