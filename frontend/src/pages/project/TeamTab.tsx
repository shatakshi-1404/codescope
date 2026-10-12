import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useState, type FormEvent } from "react";

import { RoleBadge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { ConfirmDialog } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { ErrorState } from "../../components/ui/States";
import { useToast } from "../../components/ui/Toast";
import { useAuth } from "../../auth/AuthContext";
import { api } from "../../lib/endpoints";
import { messageOf } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { can, ROLE_HELP } from "../../lib/permissions";
import type { Member, Project, Role } from "../../lib/types";

const title = (s: string) => s.charAt(0) + s.slice(1).toLowerCase();

export default function TeamTab({ project }: { project: Project }) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const me = project.my_role;

  const canInvite = can(me, "manage_members");
  const canChangeRoles = can(me, "change_roles");
  // Only the owner may create admins (the server enforces this too).
  const assignable: Role[] = me === "OWNER" ? ["ADMIN", "MEMBER", "VIEWER"] : ["MEMBER", "VIEWER"];

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("MEMBER");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<Member | null>(null);

  const q = useQuery({ queryKey: ["members", project.id], queryFn: () => api.members(project.id) });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["members", project.id] });
    qc.invalidateQueries({ queryKey: ["activity", project.id] });
  };

  const invite = useMutation({
    mutationFn: () => api.inviteMember(project.id, { email: email.trim(), role }),
    onSuccess: (m) => {
      toast.success(`${m.name} was added as ${title(m.role)}.`);
      setEmail("");
      setInviteError(null);
      refresh();
    },
    onError: (err) => setInviteError(messageOf(err)),
  });

  const changeRole = useMutation({
    mutationFn: (v: { member: Member; role: Role }) => api.changeMemberRole(project.id, v.member.id, v.role),
    onSuccess: (m) => {
      toast.success(`${m.name} is now ${title(m.role)}.`);
      refresh();
    },
    onError: (err) => {
      toast.error(messageOf(err));
      refresh(); // snap the select back to the server's value
    },
  });

  const remove = useMutation({
    mutationFn: (m: Member) => api.removeMember(project.id, m.id),
    onSuccess: (_d, m) => {
      toast.success(`${m.name} was removed.`);
      setRemoving(null);
      refresh();
    },
    onError: (err) => {
      setRemoving(null);
      toast.error(messageOf(err));
    },
  });

  function onInvite(e: FormEvent) {
    e.preventDefault();
    setInviteError(null);
    if (!email.trim()) return setInviteError("Enter the email of a registered CodeScope user.");
    invite.mutate();
  }

  const canRemove = (m: Member) =>
    canInvite && m.role !== "OWNER" && !(me === "ADMIN" && m.role === "ADMIN");

  return (
    <div className="space-y-6">
      {canInvite && (
        <section className="card p-5" aria-labelledby="invite-heading">
          <h2 id="invite-heading" className="flex items-center gap-2 text-base font-semibold">
            <UserPlus className="h-4 w-4 text-brand-600" /> Add a member
          </h2>
          <p className="mt-1 text-sm text-ink-500">They need a CodeScope account first.</p>
          <form onSubmit={onInvite} className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end" noValidate>
            <div className="flex-1">
              <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="teammate@company.com" error={inviteError ?? undefined} />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="invite-role" className="block text-sm font-medium text-ink-700">Role</label>
              <Select id="invite-role" value={role} onChange={(e) => setRole(e.target.value as Role)} className="h-10 w-full sm:w-36">
                {assignable.map((r) => <option key={r} value={r}>{title(r)}</option>)}
              </Select>
            </div>
            <Button type="submit" loading={invite.isPending} className="sm:mb-[1px]">Add member</Button>
          </form>
          <p className="mt-3 text-xs text-ink-500">{ROLE_HELP[role]}</p>
        </section>
      )}

      {q.isPending ? (
        <Skeleton className="h-40" />
      ) : q.isError ? (
        <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <caption className="sr-only">Project members</caption>
            <thead className="border-b border-line bg-ivory-50 text-xs text-ink-500">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-medium">Member</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Role</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Added</th>
                <th scope="col" className="px-4 py-2.5 text-right font-medium"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {q.data.map((m) => (
                <tr key={m.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    <p className="font-medium text-ink-900">
                      {m.name}
                      {m.user_id === user?.id && <span className="ml-2 text-xs font-normal text-ink-400">(you)</span>}
                    </p>
                    <p className="text-xs text-ink-500">{m.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    {canChangeRoles && m.role !== "OWNER" ? (
                      <Select
                        aria-label={`Role for ${m.name}`}
                        value={m.role}
                        disabled={changeRole.isPending}
                        onChange={(e) => changeRole.mutate({ member: m, role: e.target.value as Role })}
                      >
                        {assignable.map((r) => <option key={r} value={r}>{title(r)}</option>)}
                      </Select>
                    ) : (
                      <RoleBadge role={m.role} />
                    )}
                  </td>
                  <td className="px-4 py-3 text-ink-500">{formatDate(m.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    {canRemove(m) && (
                      <Button variant="ghost" size="sm" className="text-red-700 hover:bg-red-50 hover:text-red-800" onClick={() => setRemoving(m)}>
                        Remove
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={!!removing}
        title="Remove this member?"
        message={<><strong className="text-ink-900">{removing?.name}</strong> will lose access to this project immediately.</>}
        confirmLabel="Remove member"
        busy={remove.isPending}
        onConfirm={() => removing && remove.mutate(removing)}
        onCancel={() => setRemoving(null)}
      />
    </div>
  );
}
