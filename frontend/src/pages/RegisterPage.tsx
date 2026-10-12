import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { AuthLayout } from "../components/layout/AuthLayout";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { useToast } from "../components/ui/Toast";
import { fieldErrorsOf, messageOf } from "../lib/errors";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(name: string, email: string, password: string) {
  const errors: Record<string, string> = {};
  if (!name.trim()) errors.name = "Please enter your name.";
  if (!EMAIL_RE.test(email.trim())) errors.email = "Enter a valid email address.";
  if (password.length < 8) errors.password = "Use at least 8 characters.";
  else if (/^\d+$/.test(password) || /^[A-Za-z]+$/.test(password))
    errors.password = "Mix letters and numbers.";
  return errors;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const local = validate(name, email, password);
    setFieldErrors(local);
    if (Object.keys(local).length) return;

    setBusy(true);
    try {
      await register(name.trim(), email.trim(), password);
      toast.success("Account created. Welcome to CodeScope!");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      const server = fieldErrorsOf(err);
      if (Object.keys(server).length) setFieldErrors(server);
      else setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start analyzing repositories in a few minutes."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-brand-700 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && (
          <div role="alert" className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            {error}
          </div>
        )}
        <Field label="Full name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} error={fieldErrors.name} autoFocus />
        <Field label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} error={fieldErrors.email} placeholder="you@company.com" />
        <Field
          label="Password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
          hint="At least 8 characters, mixing letters and numbers."
        />
        <Button type="submit" loading={busy} className="w-full">
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
