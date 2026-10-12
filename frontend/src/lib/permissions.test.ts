import { describe, expect, it } from "vitest";

import { can, type Permission } from "./permissions";
import type { Role } from "./types";

const ALL: Permission[] = ["view_reports", "run_analysis", "edit_project", "manage_members", "change_roles", "delete_project"];

// This must mirror backend/app/core/permissions.py. If you change one, change both.
const EXPECTED: Record<Role, Permission[]> = {
  OWNER: ALL,
  ADMIN: ["view_reports", "run_analysis", "edit_project", "manage_members"],
  MEMBER: ["view_reports", "run_analysis"],
  VIEWER: ["view_reports"],
};

describe("can()", () => {
  for (const role of Object.keys(EXPECTED) as Role[]) {
    it(`${role} has exactly the expected permissions`, () => {
      for (const permission of ALL) {
        expect(can(role, permission)).toBe(EXPECTED[role].includes(permission));
      }
    });
  }
});
