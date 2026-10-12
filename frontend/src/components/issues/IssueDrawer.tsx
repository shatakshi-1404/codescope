import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, EyeOff, RotateCcw } from "lucide-react";

import { api } from "../../lib/endpoints";
import { messageOf } from "../../lib/errors";
import { formatDateTime } from "../../lib/format";
import type { IssueRow, IssueStatus } from "../../lib/types";
import { IssueStatusBadge, SeverityBadge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Drawer } from "../ui/Drawer";
import { useToast } from "../ui/Toast";

const DONE: Record<IssueStatus, string> = {
  RESOLVED: "Issue marked as resolved.",
  IGNORED: "Issue ignored. It stays ignored in future analyses.",
  OPEN: "Issue reopened.",
};

export function IssueDrawer({
  issue,
  canTriage,
  onClose,
  onChanged,
}: {
  issue: IssueRow | null;
  canTriage: boolean;
  onClose: () => void;
  onChanged: (updated: IssueRow) => void;
}) {
  const qc = useQueryClient();
  const toast = useToast();

  const m = useMutation({
    mutationFn: (v: { id: number; status: IssueStatus }) => api.setIssueStatus(v.id, v.status),
    onSuccess: (updated) => {
      for (const key of ["issues", "issues-count", "report", "dashboard", "activity"]) {
        qc.invalidateQueries({ queryKey: [key] });
      }
      onChanged({ ...issue!, ...updated });
      toast.success(DONE[updated.status]);
    },
    onError: (err) => toast.error(messageOf(err)),
  });

  async function copyLocation() {
    if (!issue) return;
    try {
      await navigator.clipboard.writeText(`${issue.file}:${issue.line}`);
      toast.success("Location copied.");
    } catch {
      toast.error("Could not copy to the clipboard.");
    }
  }

  const set = (status: IssueStatus) => issue && m.mutate({ id: issue.id, status });

  return (
    <Drawer open={!!issue} onClose={onClose} title="Issue details">
      {issue && (
        <div className="space-y-6">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={issue.severity} />
              <IssueStatusBadge status={issue.status} />
              <span className="rounded border border-line bg-ivory-100 px-1.5 py-0.5 font-mono text-xs text-ink-500">{issue.rule_id}</span>
            </div>
            <h3 className="mt-3 text-lg font-semibold leading-snug text-ink-900">{issue.title}</h3>
          </div>

          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2.5 text-sm">
            <dt className="text-ink-500">File</dt>
            <dd className="flex items-start gap-2">
              <span className="break-all font-mono text-[13px] text-ink-900">{issue.file}:{issue.line}</span>
              <button
                onClick={copyLocation}
                aria-label="Copy file location"
                className="mt-0.5 shrink-0 rounded p-0.5 text-ink-400 hover:text-ink-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                <Copy className="h-3.5 w-3.5" />
              </button>
            </dd>
            {issue.repository_name && (
              <>
                <dt className="text-ink-500">Repository</dt>
                <dd className="font-mono text-[13px] text-ink-900">{issue.repository_name}</dd>
              </>
            )}
            <dt className="text-ink-500">Category</dt>
            <dd className="capitalize text-ink-900">{issue.category.replace("-", " ")}</dd>
            {issue.resolved_at && (
              <>
                <dt className="text-ink-500">{issue.status === "IGNORED" ? "Ignored" : "Resolved"}</dt>
                <dd className="text-ink-900">{formatDateTime(issue.resolved_at)}</dd>
              </>
            )}
          </dl>

          <section>
            <h4 className="text-sm font-semibold text-ink-900">What was found</h4>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{issue.description}</p>
          </section>

          <section className="rounded-lg border border-brand-200 bg-brand-50 p-4">
            <h4 className="text-sm font-semibold text-brand-900">Recommendation</h4>
            <p className="mt-1.5 text-sm leading-relaxed text-brand-900/90">{issue.recommendation}</p>
          </section>

          {canTriage ? (
            <div className="flex flex-wrap gap-2 border-t border-line pt-5">
              {issue.status !== "RESOLVED" && (
                <Button onClick={() => set("RESOLVED")} loading={m.isPending && m.variables?.status === "RESOLVED"} disabled={m.isPending}>
                  <Check className="h-4 w-4" /> Mark resolved
                </Button>
              )}
              {issue.status !== "IGNORED" && (
                <Button variant="secondary" onClick={() => set("IGNORED")} loading={m.isPending && m.variables?.status === "IGNORED"} disabled={m.isPending}>
                  <EyeOff className="h-4 w-4" /> Ignore
                </Button>
              )}
              {issue.status !== "OPEN" && (
                <Button variant="ghost" onClick={() => set("OPEN")} loading={m.isPending && m.variables?.status === "OPEN"} disabled={m.isPending}>
                  <RotateCcw className="h-4 w-4" /> Reopen
                </Button>
              )}
            </div>
          ) : (
            <p className="border-t border-line pt-5 text-sm text-ink-500">Your role can view issues but not change their status.</p>
          )}
        </div>
      )}
    </Drawer>
  );
}
