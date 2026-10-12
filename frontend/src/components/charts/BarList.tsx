export interface BarRow {
  label: string;
  value: number;
  hint?: string;
  mono?: boolean;
}

export function BarList({ rows, emptyText = "Nothing to show." }: { rows: BarRow[]; emptyText?: string }) {
  if (rows.length === 0) return <p className="py-6 text-center text-sm text-ink-500">{emptyText}</p>;
  const max = Math.max(...rows.map((r) => r.value), 1);

  return (
    <ul className="space-y-3">
      {rows.map((r) => (
        <li key={r.label}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className={`truncate text-ink-700 ${r.mono ? "font-mono text-[13px]" : ""}`} title={r.label}>
              {r.label}
            </span>
            <span className="shrink-0 tabular-nums font-medium text-ink-900">
              {r.value.toLocaleString()}
              {r.hint && <span className="ml-1.5 text-xs font-normal text-ink-400">{r.hint}</span>}
            </span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-sage-200" aria-hidden="true">
            <div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.max((r.value / max) * 100, r.value > 0 ? 2 : 0)}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
