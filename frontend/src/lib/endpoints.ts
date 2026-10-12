import { request } from "./api";
import type {
  ActivityItem,
  AnalysisDetail,
  DashboardData,
  FileRow,
  HistoryPoint,
  InsightsData,
  Issue,
  IssueRow,
  IssueStatus,
  Member,
  Page,
  Project,
  RecentAnalysis,
  Repository,
  ReportData,
  Role,
  SecurityFinding,
  Severity,
} from "./types";

type Params = Record<string, string | number | boolean | undefined | null>;

function qs(params: Params): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

export interface IssueFilters {
  severity?: Severity;
  status?: IssueStatus;
  category?: string;
  repository_id?: number;
  limit?: number;
  offset?: number;
}

export type FileSort = "path" | "lines" | "complexity" | "functions";

export const api = {
  dashboard: () => request<DashboardData>("/dashboard"),
  myActivity: (limit: number) => request<Page<ActivityItem>>(`/activity${qs({ limit })}`),

  // projects & members
  projects: () => request<Project[]>("/projects"),
  project: (id: number) => request<Project>(`/projects/${id}`),
  createProject: (body: { name: string; description: string | null }) =>
    request<Project>("/projects", { method: "POST", body }),
  updateProject: (id: number, body: { name?: string; description?: string | null }) =>
    request<Project>(`/projects/${id}`, { method: "PATCH", body }),
  deleteProject: (id: number) => request<null>(`/projects/${id}`, { method: "DELETE" }),

  members: (id: number) => request<Member[]>(`/projects/${id}/members`),
  inviteMember: (id: number, body: { email: string; role: Role }) =>
    request<Member>(`/projects/${id}/members`, { method: "POST", body }),
  changeMemberRole: (id: number, memberId: number, role: Role) =>
    request<Member>(`/projects/${id}/members/${memberId}`, { method: "PATCH", body: { role } }),
  removeMember: (id: number, memberId: number) =>
    request<null>(`/projects/${id}/members/${memberId}`, { method: "DELETE" }),

  // repositories
  repositories: (id: number) => request<Repository[]>(`/projects/${id}/repositories`),
  addRepository: (id: number, url: string) =>
    request<Repository>(`/projects/${id}/repositories`, { method: "POST", body: { url } }),
  analyze: (repositoryId: number, branch: string) =>
    request<{ id: number }>(`/repositories/${repositoryId}/analyze`, {
      method: "POST",
      body: { branch: branch.trim() || null },
    }),
  history: (repositoryId: number) => request<HistoryPoint[]>(`/repositories/${repositoryId}/history`),

  // project-level lists
  projectAnalyses: (id: number, limit: number, offset = 0) =>
    request<Page<RecentAnalysis>>(`/projects/${id}/analyses${qs({ limit, offset })}`),
  projectIssues: (id: number, filters: IssueFilters = {}) =>
    request<Page<IssueRow>>(`/projects/${id}/issues${qs({ ...filters })}`),
  projectActivity: (id: number, limit: number) =>
    request<Page<ActivityItem>>(`/projects/${id}/activity${qs({ limit })}`),

  // analyses
  analysis: (id: number) => request<AnalysisDetail>(`/analyses/${id}`),
  report: (id: number) => request<ReportData>(`/analyses/${id}/report`),
  insights: (id: number) => request<InsightsData>(`/analyses/${id}/insights`),
  files: (id: number, p: { sort: FileSort; descending: boolean; limit: number; offset: number }) =>
    request<Page<FileRow>>(`/analyses/${id}/files${qs({ ...p })}`),
  analysisIssues: (id: number, filters: IssueFilters = {}) =>
    request<Page<IssueRow>>(`/analyses/${id}/issues${qs({ ...filters })}`),
  analysisSecurity: (id: number, limit: number, offset = 0) =>
    request<Page<SecurityFinding>>(`/analyses/${id}/security${qs({ limit, offset })}`),

  // issues
  setIssueStatus: (issueId: number, status: IssueStatus) =>
    request<Issue>(`/issues/${issueId}/status`, { method: "PATCH", body: { status } }),
};
