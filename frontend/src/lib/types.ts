export interface User {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface FieldDetail {
  field: string;
  message: string;
}

export interface ForgotPasswordResponse {
  message: string;
  dev_reset_token: string | null;
}

export interface MessageResponse {
  message: string;
}

export type Role = "OWNER" | "ADMIN" | "MEMBER" | "VIEWER";
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type AnalysisStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
export type IssueStatus = "OPEN" | "RESOLVED" | "IGNORED";

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Project {
  id: number;
  owner_id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  my_role: Role;
}

export interface Member {
  id: number;
  user_id: number;
  name: string;
  email: string;
  role: Role;
  created_at: string;
}

export interface LatestAnalysis {
  id: number;
  status: AnalysisStatus;
  progress: number;
  overall_score: number | null;
  created_at: string;
}

export interface Repository {
  id: number;
  project_id: number;
  url: string;
  name: string;
  default_branch: string | null;
  language: string | null;
  created_at: string;
  latest_analysis: LatestAnalysis | null;
}

export interface RecentAnalysis {
  id: number;
  project_id: number;
  repository_id: number;
  repository_name: string;
  branch: string | null;
  status: AnalysisStatus;
  progress: number;
  quality: number | null;
  issue_count: number;
  created_at: string;
}

export interface TrendPoint {
  date: string;
  quality: number;
  complexity: number;
  issues: number;
  security_findings: number;
}

export interface DashboardData {
  stats: {
    projects: number;
    repositories: number;
    repositories_analyzed: number;
    open_issues: number;
    average_quality: number | null;
  };
  issue_distribution: Record<string, number>;
  security_distribution: Record<string, number>;
  trend: TrendPoint[];
  recent_analyses: RecentAnalysis[];
}

export interface ActivityItem {
  id: number;
  project_id: number | null;
  user_id: number | null;
  user_name: string;
  action: string;
  resource_type: string | null;
  resource_id: number | null;
  detail: string;
  created_at: string;
}

export interface Scores {
  overall: number;
  code_quality: number;
  maintainability: number;
  complexity: number;
  security: number;
}

export interface AnalysisDetail {
  id: number;
  repository_id: number;
  project_id: number;
  repository_name: string;
  branch: string | null;
  commit_sha: string | null;
  status: AnalysisStatus;
  progress: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  files_analyzed: number;
  lines_analyzed: number;
  function_count: number;
  class_count: number;
  issue_count: number;
  security_finding_count: number;
  skipped_files: number;
  warnings: string[];
  scores: Scores | null;
  ai_summary: string | null;
}

export interface RuleCount {
  rule_id: string;
  name: string;
  count: number;
}

export interface QualityData {
  issues_by_severity: Record<string, number>;
  issues_by_category: Record<string, number>;
  issues_by_status: Record<string, number>;
  top_rules: RuleCount[];
}

export interface ComplexityData {
  avg_cyclomatic: number;
  max_cyclomatic: number;
  distribution: { label: string; files: number }[];
  most_complex_files: { path: string; max_complexity: number; avg_complexity: number; functions: number }[];
}

export interface SecurityData {
  label: string;
  disclaimer: string;
  total: number;
  by_severity: Record<string, number>;
  by_rule: RuleCount[];
}

export interface ArchitectureData {
  languages: { language: string; files: number; lines: number }[];
  directories: { name: string; files: number; lines: number }[];
  largest_files: { path: string; lines_of_code: number; functions: number }[];
}

export interface ReportData {
  analysis: AnalysisDetail;
  overview: {
    files_analyzed: number;
    lines_analyzed: number;
    functions: number;
    classes: number;
    issues: number;
    open_issues: number;
    security_findings: number;
  };
  scores: Scores | null;
  score_explanation: string;
  quality: QualityData;
  complexity: ComplexityData;
  security: SecurityData;
  architecture: ArchitectureData;
  ai_summary: string | null;
  ai_summary_label: string;
}

export interface FileRow {
  path: string;
  language: string;
  lines_of_code: number;
  function_count: number;
  class_count: number;
  import_count: number;
  max_complexity: number;
  avg_complexity: number;
  issue_count: number;
}

export interface HistoryPoint {
  analysis_id: number;
  number: number;
  date: string;
  branch: string | null;
  commit_sha: string | null;
  overall: number;
  code_quality: number;
  maintainability: number;
  complexity: number;
  security: number;
  issue_count: number;
  security_finding_count: number;
  avg_complexity: number;
}

export interface Issue {
  id: number;
  analysis_id: number;
  rule_id: string;
  file: string;
  line: number;
  category: string;
  severity: Severity;
  title: string;
  description: string;
  recommendation: string;
  status: IssueStatus;
  resolved_by: number | null;
  resolved_at: string | null;
}

/** Project-wide issue lists also carry the repository name. */
export interface IssueRow extends Issue {
  repository_name?: string;
}

export interface SecurityFinding {
  id: number;
  analysis_id: number;
  rule_id: string;
  file: string;
  line: number;
  severity: Severity;
  description: string;
  recommendation: string;
}

export interface Cluster {
  label: string;
  size: number;
  highest_severity: Severity;
  rule_ids: string[];
  top_terms: string[];
  top_files: string[];
  sample_ids: number[];
}

export interface InsightsData {
  label: string;
  method: string;
  summary: string | null;
  recommendations: string[];
  issue_clusters: Cluster[];
  security_clusters: Cluster[];
  clustered_issue_count: number;
  truncated: boolean;
}
