import { Activity, FolderKanban, GitBranch, LogIn, ScanSearch, SquareCheckBig, Users } from "lucide-react";
import type { ComponentType } from "react";

import { formatDateTime, timeAgo } from "../../lib/format";
import type { ActivityItem } from "../../lib/types";

function iconFor(action: string): ComponentType<{ className?: string }> {
  if (action.startsWith("login")) return LogIn;
  if (action.startsWith("project")) return FolderKanban;
  if (action.startsWith("member")) return Users;
  if (action.startsWith("repository")) return GitBranch;
  if (action.startsWith("analysis")) return ScanSearch;
  if (action.startsWith("issue")) return SquareCheckBig;
  return Activity;
}

export function ActivityList({ items }: { items: ActivityItem[] }) {
  return (
    <ol className="card divide-y divide-line">
      {items.map((a) => {
        const Icon = iconFor(a.action);
        return (
          <li key={a.id} className="flex items-start gap-3 px-4 py-3.5">
            <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-700">
              <Icon className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-ink-800">{a.detail}</p>
              <p className="mt-0.5 text-xs text-ink-400">
                {a.user_name} · <time dateTime={a.created_at} title={formatDateTime(a.created_at)}>{timeAgo(a.created_at)}</time>
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
