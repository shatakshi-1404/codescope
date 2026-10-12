import { useQuery } from "@tanstack/react-query";
import { GitBranch } from "lucide-react";
import { Link } from "react-router-dom";

import { RecentAnalysesTable, ScorePill } from "../../components/analysis/RecentAnalysesTable";
import { Skeleton } from "../../components/ui/Skeleton";
import { EmptyState } from "../../components/ui/States";
import { api } from "../../lib/endpoints";
import { timeAgo } from "../../lib/format";
import type { Project } from "../../lib/types";

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <p className="text-sm text-ink-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums text-ink-900">{children}</p>
    </div>
  );
}

export default function OverviewTab({ project }: { project: Project }) {
  const repos = useQuery({ queryKey: ["repos", project.id], queryFn: () => api.repositories(project.id) });
  const open = useQuery({
    queryKey: ["issues-count", project.id],
    queryFn: () => api.projectIssues(project.id, { status: "OPEN", limit: 1 }),
  });
  const analyses = useQuery({ queryKey: ["analyses", project.id, 5], queryFn: () => api.projectAnalyses(project.id, 5) });
  const activity = useQuery({ queryKey: ["activity", project.id, 5], queryFn: () => api.projectActivity(project.id, 5) });

  const scored = (repos.data ?? []).filter((r) => r.latest_analysis?.overall_score != null);
  const avg = scored.length
    ? scored.reduce((sum, r) => sum + (r.latest_analysis!.overall_score as number), 0) / scored.length
    : null;

  if (repos.data && repos.data.length === 0) {
    return (
      <EmptyState
        icon={GitBranch}
        title="Add your first repository"
        text="Paste a public GitHub URL on the Repositories tab, then run an analysis to see scores, issues and trends."
        action={
          <Link to={`/projects/${project.id}?tab=repositories`} className="text-sm font-medium text-brand-700 hover:underline">
            Go to repositories →
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Repositories">{repos.data ? repos.data.length : <Skeleton className="h-8 w-12" />}</Stat>
        <Stat label="Analyzed">{repos.data ? scored.length : <Skeleton className="h-8 w-12" />}</Stat>
        <Stat label="Average quality">{repos.data ? <ScorePill score={avg} /> : <Skeleton className="h-8 w-12" />}</Stat>
        <Stat label="Open issues">{open.data ? open.data.total : <Skeleton className="h-8 w-12" />}</Stat>
      </div>

      <section className="space-y-3" aria-labelledby="ov-analyses">
        <h2 id="ov-analyses" className="text-base font-semibold">Latest analyses</h2>
        {analyses.isPending ? (
          <Skeleton className="h-40" />
        ) : analyses.data && analyses.data.items.length > 0 ? (
          <RecentAnalysesTable analyses={analyses.data.items} />
        ) : (
          <p className="text-sm text-ink-500">No analyses yet. Run one from the Repositories tab.</p>
        )}
      </section>

      <section className="space-y-3" aria-labelledby="ov-activity">
        <h2 id="ov-activity" className="text-base font-semibold">Recent activity</h2>
        {activity.isPending ? (
          <Skeleton className="h-32" />
        ) : activity.data && activity.data.items.length > 0 ? (
          <ul className="card divide-y divide-line">
            {activity.data.items.map((a) => (
              <li key={a.id} className="flex items-start justify-between gap-4 px-4 py-3 text-sm">
                <span className="text-ink-700">{a.detail}</span>
                <span className="shrink-0 text-xs text-ink-400">{timeAgo(a.created_at)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-ink-500">Nothing has happened in this project yet.</p>
        )}
      </section>
    </div>
  );
}
