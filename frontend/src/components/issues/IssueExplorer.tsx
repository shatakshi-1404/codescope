import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, CircleAlert, PartyPopper } from "lucide-react";
import { useState } from "react";

import { api, type IssueFilters } from "../../lib/endpoints";
import { messageOf } from "../../lib/errors";
import type { IssueRow, IssueStatus, Severity } from "../../lib/types";
import { IssueStatusBadge, SeverityBadge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Select } from "../ui/Select";
import { Skeleton } from "../ui/Skeleton";
import { EmptyState, ErrorState } from "../ui/States";
import { IssueDrawer } from "./IssueDrawer";

export type IssueScope = { kind: "analysis"; id: number } | { kind: "project"; id: number };

const LIMIT = 25;
const SEVERITIES: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const STATUSES: IssueStatus[] = ["OPEN", "RESOLVED", "IGNORED"];
const CATEGORIES = ["complexity", "maintainability", "duplication", "unused-code", "naming"];
const title = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase().replace("-", " ");

export function IssueExplorer({
  scope,
  canTriage,
  initialStatus = "",
}: {
  scope: IssueScope;
  canTriage: boolean;
  initialStatus?: IssueStatus | "";
}) {
  const [severity, setSeverity] = useState<Severity | "">("");
  const [status, setStatus] = useState<IssueStatus | "">(initialStatus);
  const [category, setCategory] = useState("");
  const [repoId, setRepoId] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<IssueRow | null>(null);

  const filters: IssueFilters = {
    severity: severity || undefined,
    status: status || undefined,
    category: category || undefined,
    repository_id: scope.kind === "project" && repoId ? Number(repoId) : undefined,
    limit: LIMIT,
    offset,
  };

  const repos = useQuery({
    queryKey: ["repos", scope.id],
    queryFn: () => api.repositories(scope.id),
    enabled: scope.kind === "project",
  });

  const q = useQuery({
    queryKey: ["issues", scope.kind, scope.id, filters],
    queryFn: () => (scope.kind === "analysis" ? api.analysisIssues(scope.id, filters) : api.projectIssues(scope.id, filters)),
    placeholderData: (prev) => prev,
  });

  const filtered = !!(severity || status || category || repoId);
  const reset = (fn: () => void) => {
    fn();
    setOffset(0);
  };
  const clear = () => {
    setSeverity("");
    setStatus("");
    setCategory("");
    setRepoId("");
    setOffset(0);
  };

  const total = q.data?.total ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Issue filters">
        <Select aria-label="Filter by severity" value={severity} onChange={(e) => reset(() => setSeverity(e.target.value as Severity | ""))}>
          <option value="">All severities</option>
          {SEVERITIES.map((s) => <option key={s} value={s}>{title(s)}</option>)}
        </Select>
        <Select aria-label="Filter by status" value={status} onChange={(e) => reset(() => setStatus(e.target.value as IssueStatus | ""))}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => <option key={s} value={s}>{title(s)}</option>)}
        </Select>
        <Select aria-label="Filter by category" value={category} onChange={(e) => reset(() => setCategory(e.target.value))}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{title(c)}</option>)}
        </Select>
        {scope.kind === "project" && repos.data && repos.data.length > 1 && (
          <Select aria-label="Filter by repository" value={repoId} onChange={(e) => reset(() => setRepoId(e.target.value))}>
            <option value="">All repositories</option>
            {repos.data.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </Select>
        )}
        {filtered && <Button variant="ghost" size="sm" onClick={clear}>Clear filters</Button>}
        {q.data && <span className="ml-auto text-sm text-ink-500" aria-live="polite">{total.toLocaleString()} {total === 1 ? "issue" : "issues"}</span>}
      </div>

      {q.isPending ? (
        <div className="space-y-2" aria-busy="true" aria-label="Loading issues">
          {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-11" />)}
        </div>
      ) : q.isError ? (
        <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />
      ) : q.data.items.length === 0 ? (
        filtered ? (
          <EmptyState icon={CircleAlert} title="No issues match these filters" action={<Button variant="secondary" onClick={clear}>Clear filters</Button>} />
        ) : (
          <EmptyState icon={PartyPopper} title="No issues found" text="Nothing to report here. Nice work." />
        )
      ) : (
        <>
          <div className={`card overflow-x-auto transition-opacity ${q.isFetching ? "opacity-70" : ""}`}>
            <table className="w-full min-w-[760px] text-left text-sm">
              <caption className="sr-only">Issues</caption>
              <thead className="border-b border-line bg-ivory-50 text-xs text-ink-500">
                <tr>
                  <th scope="col" className="px-4 py-2.5 font-medium">Severity</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">File</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Line</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Issue</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Category</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((i) => (
                  <tr key={i.id} onClick={() => setSelected(i)} className="cursor-pointer border-b border-line last:border-0 hover:bg-ivory-50">
                    <td className="px-4 py-3"><SeverityBadge severity={i.severity} /></td>
                    <td className="max-w-[240px] px-4 py-3">
                      <span className="block truncate font-mono text-[13px] text-ink-700" title={i.file}>{i.file}</span>
                      {i.repository_name && <span className="block truncate text-xs text-ink-400">{i.repository_name}</span>}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-ink-600">{i.line}</td>
                    <td className="max-w-[300px] px-4 py-3">
                      <button
                        onClick={(e) => { e.stopPropagation(); setSelected(i); }}
                        className="block max-w-full truncate rounded text-left font-medium text-ink-900 hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                        title={i.title}
                      >
                        {i.title}
                      </button>
                    </td>
                    <td className="px-4 py-3 capitalize text-ink-600">{i.category.replace("-", " ")}</td>
                    <td className="px-4 py-3"><IssueStatusBadge status={i.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {total > LIMIT && (
            <div className="flex items-center justify-between text-sm text-ink-500">
              <span>{offset + 1}–{Math.min(offset + LIMIT, total)} of {total.toLocaleString()}</span>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setOffset((o) => Math.max(0, o - LIMIT))} disabled={offset === 0}>
                  <ChevronLeft className="h-4 w-4" /> Previous
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setOffset((o) => o + LIMIT)} disabled={offset + LIMIT >= total}>
                  Next <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      <IssueDrawer issue={selected} canTriage={canTriage} onClose={() => setSelected(null)} onChanged={setSelected} />
    </div>
  );
}
