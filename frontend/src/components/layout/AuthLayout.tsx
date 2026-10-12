import { Link } from "react-router-dom";
import { Check } from "lucide-react";
import type { ReactNode } from "react";

import { Wordmark } from "../ui/Logo";

const POINTS = [
  "Python, JavaScript and TypeScript analysis",
  "Deterministic, explainable quality scores",
  "Static security checks, clearly labelled",
  "Track improvement across every analysis",
];

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
      <main className="flex flex-col px-5 py-8 sm:px-10">
        <Link to="/" aria-label="CodeScope home" className="w-fit rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
          <Wordmark />
        </Link>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="text-2xl font-semibold tracking-tight text-ink-900">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-ink-500">{subtitle}</p>}
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-6 text-center text-sm text-ink-500">{footer}</div>}
        </div>
      </main>

      <aside className="hidden bg-brand-800 px-12 py-14 text-brand-50 lg:flex lg:flex-col lg:justify-center">
        <p className="font-mono text-xs uppercase tracking-widest text-brand-300">CodeScope</p>
        <h2 className="mt-4 max-w-md text-3xl font-semibold leading-tight tracking-tight text-white">
          Understand your codebase. Improve your engineering.
        </h2>
        <ul className="mt-10 space-y-4">
          {POINTS.map((p) => (
            <li key={p} className="flex items-start gap-3 text-sm text-brand-100">
              <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-600">
                <Check className="h-3 w-3 text-white" strokeWidth={3} />
              </span>
              {p}
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
