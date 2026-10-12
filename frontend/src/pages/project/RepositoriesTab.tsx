import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, GitBranch, Plus } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ScorePill } from "../../components/analysis/RecentAnalysesTable";
import { StatusBadge } from "../../components/ui/Badge";
import { Button, buttonClasses } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { Modal } from "../../components/ui/Modal";
import { Skeleton } from "../../components/ui/Skeleton";
import { EmptyState, ErrorState, ProgressBar } from "../../components/ui/States";
import { useToast } from "../../components/ui/Toast";
import { api } from "../../lib/endpoints";
import { messageOf } from "../../lib/errors";
import { isActive, timeAgo } from "../../lib/format";
import { can } from "../../lib/permissions";
import type { AnalysisStatus, Project, Repository } from "../../lib/types";

// ------------------------------------------------------------ add repository
function AddRepositoryModal({ project, onClose }: { project: Project; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const m = useMutation({
    mutationFn: () => api.addRepository(project.id, url.trim()),
    onSuccess: (repo) => {
      qc.invalidateQueries({ queryKey: ["repos", project.id] });
      qc.invalidateQueries({ queryKey: ["activity", project.id] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(`${repo.name} added. You can analyze it now.`);
      onClose();
    },
    onError: (err) => setError(messageOf(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!url.trim()) return setError("Paste a GitHub repository URL.");
    m.mutate();
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Add a repository"
      description="Public GitHub repositories only. CodeScope checks that it exists before saving."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={m.isPending}>Cancel</Button>
          <Button type="submit" form="add-repo-form" loading={m.isPending}>
            {m.isPending ? "Checking…" : "Add repository"}
          </Button>
        </>
      }
    >
      <form id="add-repo-form" onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        <Field label="Repository URL" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://github.com/owner/repository" inputMode="url" data-autofocus />
      </form>
    </Modal>
  );
}

// ------------------------------------------------------------------- analyze
function AnalyzeModal({ project, repo, onClose }: { project: Project; repo: Repository; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [branch, setBranch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const m = useMutation({
    mutationFn: () => api.analyze(repo.id, branch),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repos", project.id] });
      qc.invalidateQueries({ queryKey: ["activity", project.id] });
      toast.info(`Analysis of ${repo.name} started.`);
      onClose();
    },
    onError: (err) => setError(messageOf(err)),
  });

  return (
    <Modal
      open
      onClose={onClose}
      title={`Analyze ${repo.name}`}
      description="The repository is downloaded to a temporary folder, analyzed, then deleted."
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={m.isPending}>Cancel</Button>
          <Button type="submit" form="analyze-form" loading={m.isPending}>Start analysis</Button>
        </>
      }
    >
      <form
        id="analyze-form"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          m.mutate();
        }}
        className="space-y-4"
        noValidate
      >
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        <Field
          label="Branch or tag (optional)"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder={repo.default_branch ?? "default branch"}
          hint={`Leave empty to use the default branch${repo.default_branch ? ` (${repo.default_branch})` : ""}.`}
          data-autofocus
        />
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------- card
function RepoCard({ project, repo, onAnalyze }: { project: Project; repo: Repository; onAnalyze: () => void }) {
  const la = repo.latest_analysis;
  const active = isActive(la?.status);

  return (
    <article className="card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <a
            href={repo.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 font-mono text-sm font-medium text-ink-900 hover:text-brand-700"
          >
            {repo.name}
            <ExternalLink className="h-3.5 w-3.5" aria-label="opens on GitHub" />
          </a>
          <p className="mt-1 text-xs text-ink-500">
            <span className="capitalize">{repo.language ?? "Not analyzed yet"}</span>
            {" · "}default branch {repo.default_branch ?? "—"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {la && (la.status === "COMPLETED" || la.status === "FAILED") && (
            <Link to={`/analyses/${la.id}`} className={buttonClasses("secondary", "sm")}>
              {la.status === "FAILED" ? "Details" : "View report"}
            </Link>
          )}
          {can(project.my_role, "run_analysis") && (
            <Button size="sm" onClick={onAnalyze} disabled={active}>
              {la ? "Re-analyze" : "Analyze"}
            </Button>
          )}
        </div>
      </div>

      {la && (
        <div className="mt-4 space-y-3 border-t border-line pt-4">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            <StatusBadge status={la.status as AnalysisStatus} progress={la.status === "RUNNING" ? la.progress : undefined} />
            {la.status === "COMPLETED" && (
              <span className="text-ink-600">
                Quality <ScorePill score={la.overall_score} /> <span className="text-ink-400">/ 100</span>
              </span>
            )}
            <span className="text-xs text-ink-400">{timeAgo(la.created_at)}</span>
          </div>
          {active && <ProgressBar value={la.progress} />}
          {la.status === "FAILED" && (
            <p className="text-sm text-red-700">The analysis failed. Open details to see why, or run it again.</p>
          )}
        </div>
      )}
    </article>
  );
}

// ---------------------------------------------------------------------- tab
export default function RepositoriesTab({ project }: { project: Project }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [adding, setAdding] = useState(false);
  const [analyzing, setAnalyzing] = useState<Repository | null>(null);

  const q = useQuery({
    queryKey: ["repos", project.id],
    queryFn: () => api.repositories(project.id),
    refetchInterval: (query) => (query.state.data?.some((r) => isActive(r.latest_analysis?.status)) ? 2000 : false),
  });

  // Detect running -> finished transitions (first load never toasts).
  const previous = useRef<Map<number, AnalysisStatus>>(new Map());
  useEffect(() => {
    if (!q.data) return;
    let finished = false;
    for (const r of q.data) {
      const status = r.latest_analysis?.status;
      if (!status) continue;
      const before = previous.current.get(r.id);
      if (before && isActive(before) && status === "COMPLETED") {
        const score = r.latest_analysis?.overall_score;
        toast.success(`Analysis of ${r.name} finished${score != null ? `: quality ${Math.round(score)}/100` : ""}.`);
        finished = true;
      } else if (before && isActive(before) && status === "FAILED") {
        toast.error(`Analysis of ${r.name} failed.`);
        finished = true;
      }
      previous.current.set(r.id, status);
    }
    if (finished) {
      qc.invalidateQueries({ queryKey: ["analyses", project.id] });
      qc.invalidateQueries({ queryKey: ["issues-count", project.id] });
      qc.invalidateQueries({ queryKey: ["activity", project.id] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    }
  }, [q.data, project.id, qc, toast]);

  const canAdd = can(project.my_role, "edit_project");
  const addButton = canAdd ? (
    <Button onClick={() => setAdding(true)}>
      <Plus className="h-4 w-4" /> Add repository
    </Button>
  ) : null;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold">Repositories</h2>
        {q.data && q.data.length > 0 && addButton}
      </div>

      {q.isPending ? (
        <div className="space-y-4" aria-busy="true"><Skeleton className="h-28" /><Skeleton className="h-28" /></div>
      ) : q.isError ? (
        <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />
      ) : q.data.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title="No repositories yet"
          text={canAdd ? "Add a public GitHub repository to analyze its quality, complexity and security." : "An owner or admin needs to add a repository."}
          action={addButton}
        />
      ) : (
        <div className="space-y-4">
          {q.data.map((r) => (
            <RepoCard key={r.id} project={project} repo={r} onAnalyze={() => setAnalyzing(r)} />
          ))}
        </div>
      )}

      {adding && <AddRepositoryModal project={project} onClose={() => setAdding(false)} />}
      {analyzing && <AnalyzeModal project={project} repo={analyzing} onClose={() => setAnalyzing(null)} />}
    </div>
  );
}
