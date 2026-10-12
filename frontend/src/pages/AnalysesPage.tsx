import { useQueries, useQuery } from "@tanstack/react-query";
import { ScanSearch } from "lucide-react";
import { Link } from "react-router-dom";

import { RecentAnalysesTable } from "../components/analysis/RecentAnalysesTable";
import { buttonClasses } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState, ErrorState } from "../components/ui/States";
import { api } from "../lib/endpoints";
import { messageOf } from "../lib/errors";
import type { RecentAnalysis } from "../lib/types";

const PER_PROJECT = 10;

export default function AnalysesPage() {
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const results = useQueries({
    queries: (projects.data ?? []).map((p) => ({
      queryKey: ["analyses", p.id, PER_PROJECT],
      queryFn: () => api.projectAnalyses(p.id, PER_PROJECT),
      refetchInterval: (query: { state: { data?: { items: RecentAnalysis[] } } }) =>
        query.state.data?.items.some((a) => a.status === "PENDING" || a.status === "RUNNING") ? 3000 : (false as const),
    })),
  });

  const header = (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">Analyses</h1>
      <p className="mt-1 text-sm text-ink-500">Your most recent analyses across all projects.</p>
    </div>
  );

  if (projects.isPending || results.some((r) => r.isPending)) {
    return <div className="space-y-6">{header}<Skeleton className="h-64" /></div>;
  }
  if (projects.isError) return <div className="space-y-6">{header}<ErrorState message={messageOf(projects.error)} onRetry={() => projects.refetch()} /></div>;

  const failed = results.find((r) => r.isError);
  const items = results
    .flatMap((r) => r.data?.items ?? [])
    .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id)
    .slice(0, 50);

  return (
    <div className="space-y-6">
      {header}
      {failed && <ErrorState message={messageOf(failed.error)} onRetry={() => failed.refetch()} />}
      {items.length === 0 && !failed ? (
        <EmptyState
          icon={ScanSearch}
          title="No analyses yet"
          text="Run an analysis from a project's Repositories tab."
          action={<Link to="/projects" className={buttonClasses("primary", "md")}>Go to projects</Link>}
        />
      ) : (
        items.length > 0 && (
          <>
            <RecentAnalysesTable analyses={items} />
            <p className="text-xs text-ink-400">Showing the latest {PER_PROJECT} analyses per project. Open a project for its full history.</p>
          </>
        )
      )}
    </div>
  );
}
