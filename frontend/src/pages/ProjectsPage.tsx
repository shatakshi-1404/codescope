import { useQuery } from "@tanstack/react-query";
import { FolderKanban, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { ProjectFormModal } from "../components/project/ProjectFormModal";
import { RoleBadge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState, ErrorState } from "../components/ui/States";
import { api } from "../lib/endpoints";
import { messageOf } from "../lib/errors";
import { formatDate } from "../lib/format";

export default function ProjectsPage() {
  const [creating, setCreating] = useState(false);
  const q = useQuery({ queryKey: ["projects"], queryFn: api.projects });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="mt-1 text-sm text-ink-500">Projects you own or have been invited to.</p>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus className="h-4 w-4" /> New project
        </Button>
      </div>

      {q.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true" aria-label="Loading projects">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-[132px]" />)}
        </div>
      ) : q.isError ? (
        <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />
      ) : q.data.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects yet"
          text="Create a project to start analyzing GitHub repositories with your team."
          action={<Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New project</Button>}
        />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {q.data.map((p) => (
            <li key={p.id}>
              <Link
                to={`/projects/${p.id}`}
                className="card card-hover block h-full p-5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="truncate text-base font-semibold text-ink-900">{p.name}</h2>
                  <RoleBadge role={p.my_role} />
                </div>
                <p className="mt-2 line-clamp-2 min-h-[2.5rem] text-sm text-ink-500">
                  {p.description || "No description."}
                </p>
                <p className="mt-4 text-xs text-ink-400">Created {formatDate(p.created_at)}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {creating && <ProjectFormModal onClose={() => setCreating(false)} />}
    </div>
  );
}
