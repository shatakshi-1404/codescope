import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";

import { AuthLayout } from "../components/layout/AuthLayout";
import { Button, buttonClasses } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { useToast } from "../components/ui/Toast";
import { authApi } from "../lib/api";
import { fieldErrorsOf, messageOf } from "../lib/errors";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const toast = useToast();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const local: Record<string, string> = {};
    if (password.length < 8) local.new_password = "Use at least 8 characters.";
    else if (/^\d+$/.test(password) || /^[A-Za-z]+$/.test(password))
      local.new_password = "Mix letters and numbers.";
    if (confirm !== password) local.confirm = "Passwords do not match.";
    setFieldErrors(local);
    if (Object.keys(local).length) return;

    setBusy(true);
    try {
      const res = await authApi.resetPassword(token, password);
      toast.success(res.message);
      navigate("/login", { replace: true });
    } catch (err) {
      const server = fieldErrorsOf(err);
      if (Object.keys(server).length) setFieldErrors(server);
      else setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <AuthLayout title="Invalid reset link" subtitle="This link is missing its token.">
        <Link to="/forgot-password" className={buttonClasses("primary", "md", "w-full")}>
          Request a new link
        </Link>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Choose a new password" subtitle="You'll be signed out on all devices.">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && (
          <div role="alert" className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {error}{" "}
              <Link to="/forgot-password" className="font-medium underline">
                Request a new link
              </Link>
            </span>
          </div>
        )}
        <Field label="New password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} error={fieldErrors.new_password} hint="At least 8 characters, mixing letters and numbers." autoFocus />
        <Field label="Confirm password" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} error={fieldErrors.confirm} />
        <Button type="submit" loading={busy} className="w-full">
          Update password
        </Button>
      </form>
    </AuthLayout>
  );
}
