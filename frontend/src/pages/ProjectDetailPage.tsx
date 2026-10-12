import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleAlert, Pencil, Trash2 } from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { IssueExplorer } from "../components/issues/IssueExplorer";
import { ProjectFormModal } from "../components/project/ProjectFormModal";
import { RoleBadge } from "../components/ui/Badge";
import { Button, buttonClasses } from "../components/ui/Button";
import { ConfirmDialog } from "../components/ui/Modal";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState, ErrorState } from "../components/ui/States";
import { useToast } from "../components/ui/Toast";
import { api } from "../lib/endpoints";
import { ApiError } from "../lib/api";
import { messageOf } from "../lib/errors";
import { can } from "../lib/permissions";
import type { Project } from "../lib/types";
import ActivityTab from "./project/ActivityTab";
import AnalysesTab from "./project/AnalysesTab";
import OverviewTab from "./project/OverviewTab";
import RepositoriesTab from "./project/RepositoriesTab";
import TeamTab from "./project/TeamTab";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "repositories", label: "Repositories" },
  { id: "analyses", label: "Analyses" },
  { id: "issues", label: "Issues" },
  { id: "team", label: "Team" },
  { id: "activity", label: "Activity" },
] as const;
type TabId = (typeof TABS)[number]["id"];
const isTab = (v: string | null): v is TabId => TABS.some((t) => t.id === v);

function Panel({ project, tab }: { project: Project; tab: TabId }) {
  switch (tab) {
    case "overview": return <OverviewTab project={project} />;
    case "repositories": return <RepositoriesTab project={project} />;
    case "analyses": return <AnalysesTab project={project} />;
    case "issues":
      return (
        <IssueExplorer
          scope={{ kind: "project", id: project.id }}
          canTriage={can(project.my_role, "run_analysis")}
          initialStatus="OPEN"
        />
      );
    case "team": return <TeamTab project={project} />;
    case "activity": return <ActivityTab project={project} />;
  }
}

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const validId = Number.isInteger(id) && id > 0;

  const [params, setParams] = useSearchParams();
  const tab: TabId = isTab(params.get("tab")) ? (params.get("tab") as TabId) : "overview";

  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const q = useQuery({ queryKey: ["project", id], queryFn: () => api.project(id), enabled: validId });

  const del = useMutation({
    mutationFn: () => api.deleteProject(id),
    onSuccess: () => {
      toast.success("Project deleted.");
      qc.removeQueries({ queryKey: ["project", id] });
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      navigate("/projects", { replace: true });
    },
    onError: (err) => {
      setDeleting(false);
      toast.error(messageOf(err));
    },
  });

  function selectTab(next: TabId) {
    setParams(next === "overview" ? {} : { tab: next }, { replace: true });
  }

  function onTabKey(e: KeyboardEvent<HTMLDivElement>) {
    const index = TABS.findIndex((t) => t.id === tab);
    let next = -1;
    if (e.key === "ArrowRight") next = (index + 1) % TABS.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + TABS.length) % TABS.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = TABS.length - 1;
    if (next === -1) return;
    e.preventDefault();
    selectTab(TABS[next].id);
    document.getElementById(`tab-${TABS[next].id}`)?.focus();
  }

  const backLink = (
    <Link to="/projects" className="inline-flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-900">
      <ArrowLeft className="h-4 w-4" /> Projects
    </Link>
  );

  if (!validId || (q.isError && q.error instanceof ApiError && q.error.status === 404)) {
    return (
      <div className="space-y-6">
        {backLink}
        <EmptyState
          icon={CircleAlert}
          title="Project not found"
          text="It may have been deleted, or you don't have access to it."
          action={<Link to="/projects" className={buttonClasses("primary", "md")}>Back to projects</Link>}
        />
      </div>
    );
  }

  if (q.isPending) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading project">
        {backLink}
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-10 w-full max-w-xl" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (q.isError) {
    return (
      <div className="space-y-6">
        {backLink}
        <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />
      </div>
    );
  }

  const project = q.data;

  return (
    <div className="space-y-6">
      {backLink}

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="truncate text-2xl font-semibold tracking-tight">{project.name}</h1>
            <RoleBadge role={project.my_role} />
          </div>
          {project.description && <p className="mt-1.5 max-w-2xl text-sm text-ink-500">{project.description}</p>}
        </div>
        <div className="flex gap-2">
          {can(project.my_role, "edit_project") && (
            <Button variant="secondary" onClick={() => setEditing(true)}>
              <Pencil className="h-4 w-4" /> Edit
            </Button>
          )}
          {can(project.my_role, "delete_project") && (
            <Button variant="secondary" className="text-red-700 hover:border-red-300 hover:bg-red-50" onClick={() => setDeleting(true)}>
              <Trash2 className="h-4 w-4" /> Delete
            </Button>
          )}
        </div>
      </header>

      <div className="overflow-x-auto border-b border-line">
        <div role="tablist" aria-label="Project sections" onKeyDown={onTabKey} className="flex min-w-max gap-1">
          {TABS.map((t) => {
            const selected = t.id === tab;
            return (
              <button
                key={t.id}
                id={`tab-${t.id}`}
                role="tab"
                aria-selected={selected}
                aria-controls={`panel-${t.id}`}
                tabIndex={selected ? 0 : -1}
                onClick={() => selectTab(t.id)}
                className={
                  "-mb-px border-b-2 px-3.5 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500 " +
                  (selected ? "border-brand-700 text-brand-800" : "border-transparent text-ink-500 hover:text-ink-900")
                }
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        <Panel project={project} tab={tab} />
      </div>

      {editing && <ProjectFormModal project={project} onClose={() => setEditing(false)} />}
      <ConfirmDialog
        open={deleting}
        title="Delete this project?"
        message={
          <>
            <strong className="text-ink-900">{project.name}</strong> and all of its repositories, analyses, issues and
            activity will be permanently deleted. This cannot be undone.
          </>
        }
        confirmLabel="Delete project"
        busy={del.isPending}
        onConfirm={() => del.mutate()}
        onCancel={() => setDeleting(false)}
      />
    </div>
  );
}
