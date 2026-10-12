import { Link } from "react-router-dom";

import { formatDateTime, scoreTone, timeAgo } from "../../lib/format";
import type { RecentAnalysis } from "../../lib/types";
import { StatusBadge } from "../ui/Badge";
import { buttonClasses } from "../ui/Button";

export function ScorePill({ score }: { score: number | null }) {
  if (score === null) return <span className="text-ink-400">—</span>;
  return <span className={`font-semibold tabular-nums ${scoreTone(score)}`}>{Math.round(score)}</span>;
}

export function RecentAnalysesTable({ analyses }: { analyses: RecentAnalysis[] }) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[680px] text-left text-sm">
        <caption className="sr-only">Recent analyses</caption>
        <thead className="border-b border-line bg-ivory-50 text-xs text-ink-500">
          <tr>
            <th scope="col" className="px-4 py-2.5 font-medium">Repository</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Branch</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Status</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Quality</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Issues</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Date</th>
            <th scope="col" className="px-4 py-2.5 text-right font-medium">Report</th>
          </tr>
        </thead>
        <tbody>
          {analyses.map((a) => (
            <tr key={a.id} className="border-b border-line last:border-0 hover:bg-ivory-50">
              <td className="px-4 py-3 font-mono text-[13px] text-ink-900">{a.repository_name}</td>
              <td className="px-4 py-3 font-mono text-[13px] text-ink-600">{a.branch ?? "—"}</td>
              <td className="px-4 py-3">
                <StatusBadge status={a.status} progress={a.status === "RUNNING" ? a.progress : undefined} />
              </td>
              <td className="px-4 py-3"><ScorePill score={a.quality} /></td>
              <td className="px-4 py-3 tabular-nums text-ink-700">{a.status === "COMPLETED" ? a.issue_count : "—"}</td>
              <td className="px-4 py-3 text-ink-500" title={formatDateTime(a.created_at)}>{timeAgo(a.created_at)}</td>
              <td className="px-4 py-3 text-right">
                {a.status === "COMPLETED" || a.status === "FAILED" ? (
                  <Link to={`/analyses/${a.id}`} className={buttonClasses("secondary", "sm")}>
                    {a.status === "FAILED" ? "Details" : "View report"}
                  </Link>
                ) : (
                  <span className="text-xs text-ink-400">In progress</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
