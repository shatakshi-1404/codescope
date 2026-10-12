import { useQuery } from "@tanstack/react-query";
import { AlignLeft, ArrowLeft, Boxes, Braces, CircleAlert, Clock, FileCode2, GitBranch, Hash, ShieldAlert, Sparkles } from "lucide-react";
import type { ComponentType } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { IssueExplorer } from "../components/issues/IssueExplorer";
import { ScoreSection } from "../components/report/ScoreCards";
import {
  ArchitectureSection,
  ComplexitySection,
  FilesSection,
  HistorySection,
  InsightsSection,
  QualitySection,
  SecuritySection,
} from "../components/report/ReportSections";
import { StatusBadge } from "../components/ui/Badge";
import { buttonClasses } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState, ErrorState, ProgressBar } from "../components/ui/States";
import { panelDomId, tabDomId, Tabs } from "../components/ui/Tabs";
import { ApiError } from "../lib/api";
import { api } from "../lib/endpoints";
import { messageOf } from "../lib/errors";
import { formatDateTime, formatNumber, isActive, shortSha } from "../lib/format";
import { can } from "../lib/permissions";

const TABS = [
  { id: "quality", label: "Quality" },
  { id: "complexity", label: "Complexity" },
  { id: "security", label: "Security" },
  { id: "architecture", label: "Architecture" },
  { id: "files", label: "Files" },
  { id: "issues", label: "Issues" },
  { id: "insights", label: "AI insights" },
  { id: "history", label: "History" },
] as const;
type SectionId = (typeof TABS)[number]["id"];
const isSection = (v: string | null): v is SectionId => TABS.some((t) => t.id === v);

function OverviewCard({ icon: Icon, label, value }: { icon: ComponentType<{ className?: string }>; label: string; value: number }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-ink-500">{label}</p>
        <Icon className="h-4 w-4 text-brand-600" aria-hidden="true" />
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums text-ink-900">{formatNumber(value)}</p>
    </div>
  );
}

export default function AnalysisReportPage() {
  const { analysisId } = useParams();
  const id = Number(analysisId);
  const valid = Number.isInteger(id) && id > 0;

  const [params, setParams] = useSearchParams();
  const section: SectionId = isSection(params.get("section")) ? (params.get("section") as SectionId) : "quality";

  const aq = useQuery({
    queryKey: ["analysis", id],
    queryFn: () => api.analysis(id),
    enabled: valid,
    refetchInterval: (query) => (isActive(query.state.data?.status) ? 2000 : false),
  });
  const a = aq.data;

  const projectQ = useQuery({
    queryKey: ["project", a?.project_id],
    queryFn: () => api.project(a!.project_id),
    enabled: !!a,
  });
  const reportQ = useQuery({
    queryKey: ["report", id],
    queryFn: () => api.report(id),
    enabled: a?.status === "COMPLETED",
  });

  const canTriage = projectQ.data ? can(projectQ.data.my_role, "run_analysis") : false;

  const back = (
    <Link to={a ? `/projects/${a.project_id}?tab=repositories` : "/analyses"} className="inline-flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-900">
      <ArrowLeft className="h-4 w-4" /> {projectQ.data ? projectQ.data.name : "Analyses"}
    </Link>
  );

  if (!valid || (aq.isError && aq.error instanceof ApiError && aq.error.status === 404)) {
    return (
      <div className="space-y-6">
        {back}
        <EmptyState
          icon={CircleAlert}
          title="Report not found"
          text="It may have been deleted, or you don't have access to it."
          action={<Link to="/analyses" className={buttonClasses("primary", "md")}>Back to analyses</Link>}
        />
      </div>
    );
  }
  if (aq.isPending) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading report">
        {back}
        <Skeleton className="h-16 w-96 max-w-full" />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">{[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-[84px]" />)}</div>
        <Skeleton className="h-52" />
      </div>
    );
  }
  if (aq.isError) {
    return (
      <div className="space-y-6">
        {back}
        <ErrorState message={messageOf(aq.error)} onRetry={() => aq.refetch()} />
      </div>
    );
  }

  const header = (
    <header className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="break-all font-mono text-xl font-semibold tracking-tight text-ink-900">{a!.repository_name}</h1>
        <StatusBadge status={a!.status} progress={a!.status === "RUNNING" ? a!.progress : undefined} />
      </div>
      <p className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm text-ink-500">
        <span className="inline-flex items-center gap-1.5"><GitBranch className="h-3.5 w-3.5" aria-hidden="true" /> {a!.branch ?? "—"}</span>
        <span className="inline-flex items-center gap-1.5"><Hash className="h-3.5 w-3.5" aria-hidden="true" /> <span className="font-mono">{shortSha(a!.commit_sha)}</span></span>
        <span className="inline-flex items-center gap-1.5"><Clock className="h-3.5 w-3.5" aria-hidden="true" /> {formatDateTime(a!.completed_at ?? a!.created_at)}</span>
      </p>
    </header>
  );

  // ---- not finished yet
  if (isActive(a!.status)) {
    return (
      <div className="space-y-6">
        {back}
        {header}
        <section className="card space-y-3 p-6" role="status" aria-live="polite">
          <p className="text-sm font-medium text-ink-900">{a!.status === "PENDING" ? "Waiting for a free analysis slot…" : "Analyzing the repository…"}</p>
          <ProgressBar value={a!.progress} />
          <p className="text-xs text-ink-500">This page updates automatically. You can leave and come back.</p>
        </section>
      </div>
    );
  }

  if (a!.status === "FAILED") {
    return (
      <div className="space-y-6">
        {back}
        {header}
        <div role="alert" className="card border-red-200 p-6">
          <p className="text-sm font-semibold text-red-800">The analysis failed</p>
          <p className="mt-2 text-sm text-ink-700">{a!.error_message ?? "An unknown error occurred."}</p>
          <Link to={`/projects/${a!.project_id}?tab=repositories`} className={buttonClasses("secondary", "sm", "mt-4")}>Back to repositories to try again</Link>
        </div>
      </div>
    );
  }

  // ---- completed
  if (reportQ.isPending) {
    return (
      <div className="space-y-6" aria-busy="true">
        {back}{header}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">{[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-[84px]" />)}</div>
        <Skeleton className="h-52" />
      </div>
    );
  }
  if (reportQ.isError) {
    return (
      <div className="space-y-6">
        {back}{header}
        <ErrorState message={messageOf(reportQ.error)} onRetry={() => reportQ.refetch()} />
      </div>
    );
  }

  const r = reportQ.data;
  const notes = [...a!.warnings, ...(a!.skipped_files > 0 ? [`${a!.skipped_files} file(s) were skipped (too large, unreadable or over the file limit).`] : [])];

  return (
    <div className="space-y-6">
      {back}
      {header}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <OverviewCard icon={FileCode2} label="Files analyzed" value={r.overview.files_analyzed} />
        <OverviewCard icon={AlignLeft} label="Lines analyzed" value={r.overview.lines_analyzed} />
        <OverviewCard icon={Braces} label="Functions" value={r.overview.functions} />
        <OverviewCard icon={Boxes} label="Classes" value={r.overview.classes} />
        <OverviewCard icon={CircleAlert} label="Issues" value={r.overview.issues} />
        <OverviewCard icon={ShieldAlert} label="Security findings" value={r.overview.security_findings} />
      </div>

      {r.scores && <ScoreSection scores={r.scores} explanation={r.score_explanation} />}

      {r.ai_summary && (
        <section className="card p-5" aria-labelledby="summary-heading">
          <h2 id="summary-heading" className="flex items-center gap-2 text-sm font-semibold text-ink-900">
            <Sparkles className="h-4 w-4 text-brand-600" aria-hidden="true" /> Summary
            <span className="rounded border border-brand-200 bg-brand-50 px-1.5 py-0.5 text-[11px] font-medium text-brand-800">Automated</span>
          </h2>
          <p className="mt-2.5 text-sm leading-relaxed text-ink-700">{r.ai_summary}</p>
          <p className="mt-2 text-xs text-ink-400">{r.ai_summary_label}</p>
        </section>
      )}

      {notes.length > 0 && (
        <details className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <summary className="cursor-pointer font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500">
            Notes about this analysis ({notes.length})
          </summary>
          <ul className="mt-2 list-disc space-y-1 pl-5">{notes.map((n, i) => <li key={i} className="break-words">{n}</li>)}</ul>
        </details>
      )}

      <Tabs
        tabs={TABS}
        value={section}
        onChange={(next) => setParams(next === "quality" ? {} : { section: next }, { replace: true })}
        label="Report sections"
        prefix="report"
      />

      <div role="tabpanel" id={panelDomId("report", section)} aria-labelledby={tabDomId("report", section)}>
        {section === "quality" && <QualitySection report={r} />}
        {section === "complexity" && <ComplexitySection report={r} />}
        {section === "security" && <SecuritySection report={r} />}
        {section === "architecture" && <ArchitectureSection report={r} />}
        {section === "files" && <FilesSection analysisId={id} />}
        {section === "issues" && <IssueExplorer scope={{ kind: "analysis", id }} canTriage={canTriage} />}
        {section === "insights" && <InsightsSection analysisId={id} />}
        {section === "history" && <HistorySection repositoryId={a!.repository_id} currentId={id} />}
      </div>
    </div>
  );
}
