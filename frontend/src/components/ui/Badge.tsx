import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";

import type { AnalysisStatus, IssueStatus, Role, Severity } from "../../lib/types";

const BASE = "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs font-medium";

const SEVERITY: Record<Severity, string> = {
  CRITICAL: "border-red-200 bg-red-100 text-red-800",
  HIGH: "border-orange-200 bg-orange-100 text-orange-800",
  MEDIUM: "border-amber-200 bg-amber-100 text-amber-800",
  LOW: "border-sage-300 bg-sage-100 text-ink-600",
};

const ROLE: Record<Role, string> = {
  OWNER: "border-brand-200 bg-brand-50 text-brand-800",
  ADMIN: "border-sage-300 bg-sage-100 text-ink-700",
  MEMBER: "border-line-strong bg-white text-ink-600",
  VIEWER: "border-line bg-ivory-100 text-ink-500",
};

const title = (s: string) => s.charAt(0) + s.slice(1).toLowerCase();

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`${BASE} ${SEVERITY[severity]}`}>{title(severity)}</span>;
}

export function RoleBadge({ role }: { role: Role }) {
  return <span className={`${BASE} ${ROLE[role]}`}>{title(role)}</span>;
}

const ISSUE_STATUS: Record<IssueStatus, string> = {
  OPEN: "border-amber-200 bg-amber-50 text-amber-800",
  RESOLVED: "border-brand-200 bg-brand-50 text-brand-800",
  IGNORED: "border-line bg-ivory-100 text-ink-500",
};

export function IssueStatusBadge({ status }: { status: IssueStatus }) {
  return <span className={`${BASE} ${ISSUE_STATUS[status]}`}>{title(status)}</span>;
}

export function StatusBadge({ status, progress }: { status: AnalysisStatus; progress?: number }) {
  switch (status) {
    case "COMPLETED":
      return (
        <span className={`${BASE} border-brand-200 bg-brand-50 text-brand-800`}>
          <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> Completed
        </span>
      );
    case "FAILED":
      return (
        <span className={`${BASE} border-red-200 bg-red-50 text-red-800`}>
          <XCircle className="h-3 w-3" aria-hidden="true" /> Failed
        </span>
      );
    case "RUNNING":
      return (
        <span className={`${BASE} border-sage-300 bg-sage-100 text-ink-700`}>
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> Running
          {progress !== undefined ? ` ${progress}%` : ""}
        </span>
      );
    default:
      return (
        <span className={`${BASE} border-line bg-ivory-100 text-ink-500`}>
          <CircleDashed className="h-3 w-3" aria-hidden="true" /> Queued
        </span>
      );
  }
}
