import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, MailCheck } from "lucide-react";

import { AuthLayout } from "../components/layout/AuthLayout";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { authApi } from "../lib/api";
import { messageOf } from "../lib/errors";
import type { ForgotPasswordResponse } from "../lib/types";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ForgotPasswordResponse | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      setResult(await authApi.forgotPassword(email.trim()));
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Enter your email and we'll create a reset link."
      footer={
        <Link to="/login" className="font-medium text-brand-700 hover:underline">
          Back to sign in
        </Link>
      }
    >
      {result ? (
        <div className="space-y-4" role="status">
          <div className="flex items-start gap-3 rounded-md border border-brand-200 bg-brand-50 p-4 text-sm text-brand-900">
            <MailCheck className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
            <p>{result.message}</p>
          </div>
          {result.dev_reset_token && (
            <div className="rounded-md border border-dashed border-line-strong bg-ivory-200/60 p-4 text-sm text-ink-600">
              <p className="font-medium text-ink-900">Development mode</p>
              <p className="mt-1">No email provider is configured, so the reset link is shown here instead.</p>
              <Link
                to={`/reset-password?token=${encodeURIComponent(result.dev_reset_token)}`}
                className="mt-3 inline-block font-medium text-brand-700 hover:underline"
              >
                Open reset link →
              </Link>
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {error && (
            <div role="alert" className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
          <Field label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required autoFocus />
          <Button type="submit" loading={busy} className="w-full" disabled={!email}>
            Send reset link
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
