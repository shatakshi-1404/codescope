import { useQuery } from "@tanstack/react-query";
import { CircleAlert, FolderKanban, GitBranch, Plus, ScanSearch, Star } from "lucide-react";
import { useState, type ComponentType } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { RecentAnalysesTable } from "../components/analysis/RecentAnalysesTable";
import { ChartCard, SeverityBars, SeverityDonut, TrendLine } from "../components/charts/Charts";
import { ProjectFormModal } from "../components/project/ProjectFormModal";
import { Button, buttonClasses } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState, ErrorState } from "../components/ui/States";
import { formatNumber, isActive, scoreTone } from "../lib/format";
import { api } from "../lib/endpoints";
import { messageOf } from "../lib/errors";

function StatCard({ icon: Icon, label, value, hint, tone }: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
  hint?: string;
  tone?: string;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-500">{label}</p>
        <Icon className="h-4 w-4 text-brand-600" aria-hidden="true" />
      </div>
      <p className={`mt-3 text-3xl font-semibold tracking-tight tabular-nums ${tone ?? "text-ink-900"}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-500">{hint}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [creating, setCreating] = useState(false);

  const q = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
    // Keep the table fresh while something is running.
    refetchInterval: (query) => (query.state.data?.recent_analyses.some((a) => isActive(a.status)) ? 3000 : false),
  });

  const firstName = user?.name.split(" ")[0] ?? "";

  const header = (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Welcome back, {firstName}</h1>
        <p className="mt-1 text-sm text-ink-500">Here is how your codebases are doing.</p>
      </div>
      <Button onClick={() => setCreating(true)}>
        <Plus className="h-4 w-4" /> New project
      </Button>
    </div>
  );

  if (q.isPending) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading dashboard">
        {header}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[116px]" />)}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {[0, 1].map((i) => <Skeleton key={i} className="h-[300px]" />)}
        </div>
      </div>
    );
  }

  if (q.isError) {
    return (
      <div className="space-y-6">
        {header}
        <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />
      </div>
    );
  }

  const d = q.data;
  const hasAnalyses = d.recent_analyses.length > 0;
  const hasTrend = d.trend.length > 0;
  const avg = d.stats.average_quality;

  return (
    <div className="space-y-6">
      {header}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={FolderKanban} label="Projects" value={formatNumber(d.stats.projects)} />
        <StatCard
          icon={GitBranch}
          label="Repositories analyzed"
          value={`${d.stats.repositories_analyzed} / ${d.stats.repositories}`}
          hint="Latest analysis per repository"
        />
        <StatCard icon={CircleAlert} label="Open issues" value={formatNumber(d.stats.open_issues)} hint="Across latest analyses" />
        <StatCard
          icon={Star}
          label="Average quality"
          value={avg === null ? "—" : `${Math.round(avg)}`}
          hint={avg === null ? "Run an analysis to get a score" : "out of 100"}
          tone={avg === null ? "text-ink-400" : scoreTone(avg)}
        />
      </div>

      {d.stats.projects === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="Create your first project"
          text="Projects group repositories and your team. Add a public GitHub repository next, then run an analysis."
          action={<Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New project</Button>}
        />
      ) : !hasAnalyses ? (
        <EmptyState
          icon={ScanSearch}
          title="No analyses yet"
          text="Open a project, add a public GitHub repository and run your first analysis. Charts will appear here."
          action={<Link to="/projects" className={buttonClasses("primary", "md")}>Go to projects</Link>}
        />
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Code quality trend" subtitle="Average overall score per day">
              {hasTrend ? <TrendLine data={d.trend} dataKey="quality" name="Quality" domain={[0, 100]} /> : <p className="py-10 text-center text-sm text-ink-500">Complete an analysis to see the trend.</p>}
            </ChartCard>
            <ChartCard title="Complexity trend" subtitle="Average cyclomatic complexity per function (lower is better)">
              {hasTrend ? <TrendLine data={d.trend} dataKey="complexity" name="Avg. complexity" color="#667F6F" /> : <p className="py-10 text-center text-sm text-ink-500">Complete an analysis to see the trend.</p>}
            </ChartCard>
            <ChartCard title="Issue distribution" subtitle="Open issues by severity">
              <SeverityDonut counts={d.issue_distribution} centerLabel="open issues" />
            </ChartCard>
            <ChartCard title="Security findings" subtitle="Static security checks by severity (not a full audit)">
              <SeverityBars counts={d.security_distribution} />
            </ChartCard>
          </div>

          <section aria-labelledby="recent-heading" className="space-y-3">
            <h2 id="recent-heading" className="text-base font-semibold">Recent analyses</h2>
            <RecentAnalysesTable analyses={d.recent_analyses} />
          </section>
        </>
      )}

      {creating && <ProjectFormModal onClose={() => setCreating(false)} />}
    </div>
  );
}
