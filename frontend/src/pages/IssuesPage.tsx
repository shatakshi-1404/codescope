import { IssueExplorer } from "../components/issues/IssueExplorer";
import { ProjectScope } from "../components/project/ProjectScope";
import { can } from "../lib/permissions";

export default function IssuesPage() {
  return (
    <ProjectScope title="Issues" subtitle="Issues from the latest analysis of each repository in a project.">
      {(project) => (
        <IssueExplorer
          scope={{ kind: "project", id: project.id }}
          canTriage={can(project.my_role, "run_analysis")}
          initialStatus="OPEN"
        />
      )}
    </ProjectScope>
  );
}
