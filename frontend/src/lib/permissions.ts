import type { Role } from "./types";

export type Permission =
  | "view_reports"
  | "run_analysis"
  | "edit_project"
  | "manage_members"
  | "change_roles"
  | "delete_project";

const MATRIX: Record<Role, readonly Permission[]> = {
  VIEWER: ["view_reports"],
  MEMBER: ["view_reports", "run_analysis"],
  ADMIN: ["view_reports", "run_analysis", "edit_project", "manage_members"],
  OWNER: ["view_reports", "run_analysis", "edit_project", "manage_members", "change_roles", "delete_project"],
};

export const can = (role: Role, permission: Permission): boolean => MATRIX[role].includes(permission);

export const ROLE_HELP: Record<Role, string> = {
  OWNER: "Full control, including deleting the project.",
  ADMIN: "Edit the project, manage members, run analyses.",
  MEMBER: "Run analyses and triage issues.",
  VIEWER: "View reports only.",
};
