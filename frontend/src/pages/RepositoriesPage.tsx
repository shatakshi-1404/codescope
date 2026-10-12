import { useQueries, useQuery } from "@tanstack/react-query";
import { ExternalLink, GitBranch } from "lucide-react";
import { Link } from "react-router-dom";

import { ScorePill } from "../components/analysis/RecentAnalysesTable";
import { RoleBadge, StatusBadge } from "../components/ui/Badge";
import { buttonClasses } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState, ErrorState } from "../components/ui/States";
import { api } from "../lib/endpoints";
import { messageOf } from "../lib/errors";
import { isActive, timeAgo } from "../lib/format";
import type { Repository } from "../lib/types";

export default function RepositoriesPage() {
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const repoQueries = useQueries({
    queries: (projects.data ?? []).map((p) => ({
      queryKey: ["repos", p.id],
      queryFn: () => api.repositories(p.id),
      refetchInterval: (query: { state: { data?: Repository[] } }) =>
        query.state.data?.some((r) => isActive(r.latest_analysis?.status)) ? 3000 : (false as const),
    })),
  });

  const header = (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">Repositories</h1>
      <p className="mt-1 text-sm text-ink-500">Every repository across your projects. Add or analyze them from the project page.</p>
    </div>
  );

  if (projects.isPending) return <div className="space-y-6">{header}<Skeleton className="h-64" /></div>;
  if (projects.isError) return <div className="space-y-6">{header}<ErrorState message={messageOf(projects.error)} onRetry={() => projects.refetch()} /></div>;

  const total = repoQueries.reduce((n, q) => n + (q.data?.length ?? 0), 0);
  const loading = repoQueries.some((q) => q.isPending);

  return (
    <div className="space-y-6">
      {header}
      {!loading && total === 0 ? (
        <EmptyState
          icon={GitBranch}
          title="No repositories yet"
          text="Open a project and add a public GitHub repository."
          action={<Link to="/projects" className={buttonClasses("primary", "md")}>Go to projects</Link>}
        />
      ) : (
        projects.data.map((p, i) => {
          const q = repoQueries[i];
          if (q?.data?.length === 0) return null;
          return (
            <section key={p.id} aria-labelledby={`proj-${p.id}`} className="space-y-3">
              <div className="flex items-center gap-3">
                <h2 id={`proj-${p.id}`} className="text-base font-semibold">
                  <Link to={`/projects/${p.id}?tab=repositories`} className="hover:text-brand-700">{p.name}</Link>
                </h2>
                <RoleBadge role={p.my_role} />
              </div>
              {!q || q.isPending ? (
                <Skeleton className="h-28" />
              ) : q.isError ? (
                <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />
              ) : (
                <div className="card overflow-x-auto">
                  <table className="w-full min-w-[680px] text-left text-sm">
                    <caption className="sr-only">Repositories in {p.name}</caption>
                    <thead className="border-b border-line bg-ivory-50 text-xs text-ink-500">
                      <tr>
                        <th scope="col" className="px-4 py-2.5 font-medium">Repository</th>
                        <th scope="col" className="px-4 py-2.5 font-medium">Language</th>
                        <th scope="col" className="px-4 py-2.5 font-medium">Latest analysis</th>
                        <th scope="col" className="px-4 py-2.5 font-medium">Quality</th>
                        <th scope="col" className="px-4 py-2.5 text-right font-medium">Report</th>
                      </tr>
                    </thead>
                    <tbody>
                      {q.data!.map((r) => (
                        <tr key={r.id} className="border-b border-line last:border-0 hover:bg-ivory-50">
                          <td className="px-4 py-3">
                            <a href={r.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 font-mono text-[13px] font-medium text-ink-900 hover:text-brand-700">
                              {r.name} <ExternalLink className="h-3 w-3" aria-label="opens on GitHub" />
                            </a>
                          </td>
                          <td className="px-4 py-3 capitalize text-ink-600">{r.language ?? "—"}</td>
                          <td className="px-4 py-3">
                            {r.latest_analysis ? (
                              <span className="flex items-center gap-2">
                                <StatusBadge status={r.latest_analysis.status} progress={r.latest_analysis.status === "RUNNING" ? r.latest_analysis.progress : undefined} />
                                <span className="text-xs text-ink-400">{timeAgo(r.latest_analysis.created_at)}</span>
                              </span>
                            ) : (
                              <span className="text-ink-400">Never analyzed</span>
                            )}
                          </td>
                          <td className="px-4 py-3"><ScorePill score={r.latest_analysis?.overall_score ?? null} /></td>
                          <td className="px-4 py-3 text-right">
                            {r.latest_analysis && (r.latest_analysis.status === "COMPLETED" || r.latest_analysis.status === "FAILED") ? (
                              <Link to={`/analyses/${r.latest_analysis.id}`} className={buttonClasses("secondary", "sm")}>Open</Link>
                            ) : (
                              <Link to={`/projects/${p.id}?tab=repositories`} className="text-xs text-brand-700 hover:underline">Manage</Link>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          );
        })
      )}
    </div>
  );
}
