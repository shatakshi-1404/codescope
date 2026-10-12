import { useQuery } from "@tanstack/react-query";
import { ScanSearch } from "lucide-react";
import { useState } from "react";

import { RecentAnalysesTable } from "../../components/analysis/RecentAnalysesTable";
import { Button } from "../../components/ui/Button";
import { Skeleton } from "../../components/ui/Skeleton";
import { EmptyState, ErrorState } from "../../components/ui/States";
import { api } from "../../lib/endpoints";
import { messageOf } from "../../lib/errors";
import { isActive } from "../../lib/format";
import type { Project } from "../../lib/types";

const STEP = 20;

export default function AnalysesTab({ project }: { project: Project }) {
  const [limit, setLimit] = useState(STEP);
  const q = useQuery({
    queryKey: ["analyses", project.id, limit],
    queryFn: () => api.projectAnalyses(project.id, limit),
    placeholderData: (prev) => prev,
    refetchInterval: (query) => (query.state.data?.items.some((a) => isActive(a.status)) ? 3000 : false),
  });

  if (q.isPending) return <Skeleton className="h-56" />;
  if (q.isError) return <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />;
  if (q.data.items.length === 0) {
    return (
      <EmptyState
        icon={ScanSearch}
        title="No analyses yet"
        text="Run an analysis from the Repositories tab. Every run is saved so you can track progress over time."
      />
    );
  }

  return (
    <div className="space-y-4">
      <RecentAnalysesTable analyses={q.data.items} />
      {q.data.total > q.data.items.length && (
        <div className="text-center">
          <Button variant="secondary" onClick={() => setLimit((l) => l + STEP)} loading={q.isFetching}>
            Show more ({q.data.total - q.data.items.length} remaining)
          </Button>
        </div>
      )}
    </div>
  );
}
