import { ProjectScope } from "../components/project/ProjectScope";
import TeamTab from "./project/TeamTab";

export default function TeamPage() {
  return (
    <ProjectScope title="Team" subtitle="Members and roles for a project.">
      {(project) => <TeamTab project={project} />}
    </ProjectScope>
  );
}
