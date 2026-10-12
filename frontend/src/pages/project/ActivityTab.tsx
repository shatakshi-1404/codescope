import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { useState } from "react";

import { ActivityList } from "../../components/activity/ActivityList";
import { Button } from "../../components/ui/Button";
import { Skeleton } from "../../components/ui/Skeleton";
import { EmptyState, ErrorState } from "../../components/ui/States";
import { api } from "../../lib/endpoints";
import { messageOf } from "../../lib/errors";
import type { Project } from "../../lib/types";

const STEP = 30;

export default function ActivityTab({ project }: { project: Project }) {
  const [limit, setLimit] = useState(STEP);
  const q = useQuery({
    queryKey: ["activity", project.id, limit],
    queryFn: () => api.projectActivity(project.id, limit),
    placeholderData: (prev) => prev,
  });

  if (q.isPending) return <Skeleton className="h-64" />;
  if (q.isError) return <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />;
  if (q.data.items.length === 0) {
    return <EmptyState icon={Activity} title="No activity yet" text="Actions like adding repositories or running analyses will be logged here." />;
  }

  return (
    <div className="space-y-4">
      <ActivityList items={q.data.items} />
      {q.data.total > q.data.items.length && (
        <div className="text-center">
          <Button variant="secondary" onClick={() => setLimit((l) => l + STEP)} loading={q.isFetching}>Show more</Button>
        </div>
      )}
    </div>
  );
}
