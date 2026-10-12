import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { useState } from "react";

import { ActivityList } from "../components/activity/ActivityList";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState, ErrorState } from "../components/ui/States";
import { api } from "../lib/endpoints";
import { messageOf } from "../lib/errors";

const STEP = 30;

export default function ActivityPage() {
  const [limit, setLimit] = useState(STEP);
  const q = useQuery({
    queryKey: ["activity", "me", limit],
    queryFn: () => api.myActivity(limit),
    placeholderData: (prev) => prev,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Activity</h1>
        <p className="mt-1 text-sm text-ink-500">An audit log across every project you belong to.</p>
      </div>
      {q.isPending ? (
        <Skeleton className="h-72" />
      ) : q.isError ? (
        <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />
      ) : q.data.items.length === 0 ? (
        <EmptyState icon={Activity} title="No activity yet" text="Creating projects, adding repositories and running analyses will appear here." />
      ) : (
        <>
          <ActivityList items={q.data.items} />
          {q.data.total > q.data.items.length && (
            <div className="text-center">
              <Button variant="secondary" onClick={() => setLimit((l) => l + STEP)} loading={q.isFetching}>Show more</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
