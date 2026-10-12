import { LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/ui/Button";
import { useToast } from "../components/ui/Toast";
import { formatDate } from "../lib/format";

const THRESHOLDS = [
  ["Function length", "more than 50 lines"],
  ["Parameters", "more than 5"],
  ["Nesting depth", "more than 4 levels"],
  ["Branches", "more than 10"],
  ["Cyclomatic complexity", "more than 15"],
  ["File size", "more than 500 lines"],
];

const POINTS = [["Low", 1], ["Medium", 3], ["High", 6], ["Critical", 12]] as const;

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  if (!user) return null;

  async function onLogout() {
    await logout();
    toast.info("You've been signed out.");
    navigate("/login", { replace: true });
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-ink-500">Your account and how CodeScope scores code.</p>
      </div>

      <section className="card p-5" aria-labelledby="account-h">
        <h2 id="account-h" className="text-base font-semibold">Account</h2>
        <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 text-sm">
          <dt className="text-ink-500">Name</dt><dd className="text-ink-900">{user.name}</dd>
          <dt className="text-ink-500">Email</dt><dd className="text-ink-900">{user.email}</dd>
          <dt className="text-ink-500">Member since</dt><dd className="text-ink-900">{formatDate(user.created_at)}</dd>
        </dl>
        <Button variant="secondary" className="mt-5" onClick={onLogout}>
          <LogOut className="h-4 w-4" /> Sign out
        </Button>
      </section>

      <section className="card p-5" aria-labelledby="rules-h">
        <h2 id="rules-h" className="text-base font-semibold">Analysis thresholds</h2>
        <p className="mt-1 text-sm text-ink-500">
          Defaults used by every analysis. They are set in <code className="rounded bg-sage-100 px-1 py-0.5 font-mono text-xs">backend/app/analysis/config.py</code>.
        </p>
        <dl className="mt-4 grid gap-x-8 gap-y-2.5 text-sm sm:grid-cols-2">
          {THRESHOLDS.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 border-b border-line pb-2">
              <dt className="text-ink-600">{k}</dt>
              <dd className="font-medium text-ink-900">{v}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="card p-5" aria-labelledby="score-h">
        <h2 id="score-h" className="text-base font-semibold">How scores work</h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-600">
          Each finding costs points by severity. Penalties are scaled per 1,000 lines so large repositories are not punished for their size.
          The overall score is the average of four dimensions: code quality, maintainability, complexity and security.
          It is a transparent heuristic, not a scientific measure, and the security score comes from static checks, not a full audit.
        </p>
        <ul className="mt-3 flex flex-wrap gap-2 text-xs">
          {POINTS.map(([name, pts]) => (
            <li key={name} className="rounded border border-line bg-ivory-50 px-2 py-1 text-ink-600">{name}: {pts} {pts === 1 ? "point" : "points"}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
