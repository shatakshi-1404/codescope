import { useQuery } from "@tanstack/react-query";
import { FolderKanban } from "lucide-react";
import { Fragment, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../../lib/endpoints";
import { messageOf } from "../../lib/errors";
import type { Project } from "../../lib/types";
import { buttonClasses } from "../ui/Button";
import { Select } from "../ui/Select";
import { Skeleton } from "../ui/Skeleton";
import { EmptyState, ErrorState } from "../ui/States";

export function ProjectScope({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: (project: Project) => ReactNode;
}) {
  const [params, setParams] = useSearchParams();
  const q = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const selected = q.data?.find((p) => String(p.id) === params.get("project")) ?? q.data?.[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-ink-500">{subtitle}</p>
        </div>
        {q.data && q.data.length > 0 && selected && (
          <div className="flex items-center gap-2">
            <label htmlFor="project-picker" className="text-sm text-ink-500">Project</label>
            <Select id="project-picker" value={selected.id} onChange={(e) => setParams({ project: e.target.value }, { replace: true })} className="max-w-[240px]">
              {q.data.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </Select>
          </div>
        )}
      </div>

      {q.isPending ? (
        <Skeleton className="h-64" />
      ) : q.isError ? (
        <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />
      ) : !selected ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects yet"
          text="Create a project first."
          action={<Link to="/projects" className={buttonClasses("primary", "md")}>Go to projects</Link>}
        />
      ) : (
        <Fragment key={selected.id}>{children(selected)}</Fragment>
      )}
    </div>
  );
}
