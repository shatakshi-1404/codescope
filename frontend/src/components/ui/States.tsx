import { AlertCircle } from "lucide-react";
import type { ComponentType, ReactNode } from "react";

import { Button } from "./Button";

export function EmptyState({
  icon: Icon,
  title,
  text,
  action,
}: {
  icon: ComponentType<{ className?: string }>;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <div className="card grid place-items-center px-6 py-14 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-full bg-brand-50 text-brand-700">
        <Icon className="h-5 w-5" />
      </span>
      <h3 className="mt-4 text-sm font-semibold text-ink-900">{title}</h3>
      {text && <p className="mt-1 max-w-sm text-sm text-ink-500">{text}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="card grid place-items-center border-red-200 px-6 py-12 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-full bg-red-50 text-red-700">
        <AlertCircle className="h-5 w-5" />
      </span>
      <p className="mt-4 max-w-md text-sm text-ink-700">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function ProgressBar({ value, label = "Analysis progress" }: { value: number; label?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      className="h-1.5 w-full overflow-hidden rounded-full bg-sage-200"
    >
      <div className="h-full rounded-full bg-brand-600 transition-all duration-500" style={{ width: `${pct}%` }} />
    </div>
  );
}
