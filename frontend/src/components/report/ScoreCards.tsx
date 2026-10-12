import { Info } from "lucide-react";

import { scoreLabel, scoreTone } from "../../lib/format";
import type { Scores } from "../../lib/types";

function ringColor(score: number) {
  if (score >= 80) return "#0F5A3F";
  if (score >= 65) return "#D97706";
  return "#B91C1C";
}

export function ScoreRing({ score, size = 132 }: { score: number; size?: number }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={`Overall score ${Math.round(score)} out of 100`}>
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#E8EFEA" strokeWidth="10" />
        <circle
          cx="60" cy="60" r={r} fill="none" stroke={ringColor(score)} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - pct / 100)}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <p className={`text-3xl font-semibold tracking-tight tabular-nums ${scoreTone(score)}`}>{Math.round(score)}</p>
          <p className="text-[11px] text-ink-500">/ 100</p>
        </div>
      </div>
    </div>
  );
}

function Dimension({ label, score }: { label: string; score: number }) {
  return (
    <div className="rounded-lg border border-line bg-ivory-50 p-4">
      <p className="text-sm text-ink-500">{label}</p>
      <p className={`mt-1.5 text-2xl font-semibold tracking-tight tabular-nums ${scoreTone(score)}`}>{Math.round(score)}</p>
      <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-sage-200" aria-hidden="true">
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: ringColor(score) }} />
      </div>
    </div>
  );
}

export function ScoreSection({ scores, explanation }: { scores: Scores; explanation: string }) {
  return (
    <section className="card p-5 sm:p-6" aria-labelledby="score-heading">
      <h2 id="score-heading" className="sr-only">Quality score</h2>
      <div className="flex flex-col gap-6 md:flex-row md:items-center">
        <div className="flex items-center gap-5">
          <ScoreRing score={scores.overall} />
          <div>
            <p className="text-sm text-ink-500">Overall</p>
            <p className="text-lg font-semibold text-ink-900">{scoreLabel(scores.overall)}</p>
          </div>
        </div>
        <div className="grid flex-1 grid-cols-2 gap-3 lg:grid-cols-4">
          <Dimension label="Code quality" score={scores.code_quality} />
          <Dimension label="Maintainability" score={scores.maintainability} />
          <Dimension label="Complexity" score={scores.complexity} />
          <Dimension label="Security" score={scores.security} />
        </div>
      </div>
      <details className="mt-5 rounded-md border border-line bg-ivory-50 px-4 py-3 text-sm">
        <summary className="flex cursor-pointer items-center gap-2 font-medium text-ink-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500">
          <Info className="h-4 w-4 text-brand-600" aria-hidden="true" /> How is this calculated?
        </summary>
        <p className="mt-3 leading-relaxed text-ink-600">{explanation}</p>
      </details>
    </section>
  );
}
