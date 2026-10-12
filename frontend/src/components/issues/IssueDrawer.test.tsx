import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api";
import { api } from "../../lib/endpoints";
import type { Issue, IssueRow } from "../../lib/types";
import { ToastProvider } from "../ui/Toast";
import { IssueDrawer } from "./IssueDrawer";

vi.mock("../../lib/endpoints", () => ({ api: { setIssueStatus: vi.fn() } }));

const base: Issue = {
  id: 7,
  analysis_id: 1,
  rule_id: "QUAL-007",
  file: "app.py",
  line: 3,
  category: "unused-code",
  severity: "LOW",
  title: "Unused import: os",
  description: "`os` is imported but never used in this file.",
  recommendation: "Remove the import.",
  status: "OPEN",
  resolved_by: null,
  resolved_at: null,
};
const issue: IssueRow = { ...base, repository_name: "acme/api" };

function setup(canTriage = true) {
  const onClose = vi.fn();
  const onChanged = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ToastProvider>
        <IssueDrawer issue={issue} canTriage={canTriage} onClose={onClose} onChanged={onChanged} />
      </ToastProvider>
    </QueryClientProvider>,
  );
  return { onClose, onChanged, user: userEvent.setup() };
}

beforeEach(() => {
  vi.mocked(api.setIssueStatus).mockReset();
});

describe("IssueDrawer", () => {
  it("shows what was found and how to fix it", () => {
    setup();
    expect(screen.getByRole("dialog", { name: "Issue details" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Unused import: os" })).toBeInTheDocument();
    expect(screen.getByText("app.py:3")).toBeInTheDocument();
    expect(screen.getByText("acme/api")).toBeInTheDocument();
    expect(screen.getByText("Remove the import.")).toBeInTheDocument();
  });

  it("offers resolve and ignore (but not reopen) for an open issue", () => {
    setup();
    expect(screen.getByRole("button", { name: /Mark resolved/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Ignore/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reopen/ })).not.toBeInTheDocument();
  });

  it("resolves the issue, reports the new state and confirms with a toast", async () => {
    vi.mocked(api.setIssueStatus).mockResolvedValue({
      ...base,
      status: "RESOLVED",
      resolved_by: 1,
      resolved_at: "2026-10-03T12:00:00Z",
    });
    const { onChanged, user } = setup();

    await user.click(screen.getByRole("button", { name: /Mark resolved/ }));

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(api.setIssueStatus).toHaveBeenCalledWith(7, "RESOLVED");
    expect(onChanged.mock.calls[0][0]).toMatchObject({ id: 7, status: "RESOLVED", repository_name: "acme/api" });
    expect(await screen.findByText("Issue marked as resolved.")).toBeInTheDocument();
  });

  it("shows the server's message when the change is refused", async () => {
    vi.mocked(api.setIssueStatus).mockRejectedValue(new ApiError(403, "forbidden", "You don't have permission to do this in this project."));
    const { onChanged, user } = setup();

    await user.click(screen.getByRole("button", { name: /Ignore/ }));

    expect(await screen.findByText("You don't have permission to do this in this project.")).toBeInTheDocument();
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("hides the actions from roles that may only view", () => {
    setup(false);
    expect(screen.getByText("Your role can view issues but not change their status.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Mark resolved/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Ignore/ })).not.toBeInTheDocument();
  });

  it("closes with the Escape key", async () => {
    const { onClose, user } = setup();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
