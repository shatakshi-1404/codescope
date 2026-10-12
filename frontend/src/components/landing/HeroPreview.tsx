const POINTS = [
  { x: 24, score: 71 },
  { x: 150, score: 78 },
  { x: 276, score: 84 },
];
const y = (score: number) => 108 - (score - 60) * 3.2;

const ROWS = [
  { repo: "acme/payments-api", q: 84, issues: 12, sev: "bg-amber-100 text-amber-800", label: "Medium" },
  { repo: "acme/web-client", q: 79, issues: 21, sev: "bg-sage-200 text-ink-700", label: "Low" },
  { repo: "acme/data-jobs", q: 66, issues: 34, sev: "bg-red-100 text-red-800", label: "High" },
];

export function HeroPreview() {
  const line = POINTS.map((p) => `${p.x},${y(p.score)}`).join(" ");
  return (
    <figure className="mx-auto w-full max-w-4xl">
      <div className="overflow-hidden rounded-xl border border-line-strong bg-white shadow-pop">
        {/* window chrome */}
        <div className="flex items-center gap-2 border-b border-line bg-ivory-100 px-4 py-2.5">
          <span className="h-2.5 w-2.5 rounded-full bg-sage-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-sage-300" />
          <span className="h-2.5 w-2.5 rounded-full bg-sage-300" />
          <span className="ml-3 truncate rounded bg-white px-2.5 py-0.5 font-mono text-[11px] text-ink-400">
            codescope.app/dashboard
          </span>
        </div>

        <div className="grid sm:grid-cols-[150px_1fr]">
          <div className="hidden space-y-1.5 border-r border-line bg-white p-3 sm:block">
            {["Dashboard", "Projects", "Analyses", "Issues", "Activity"].map((l, i) => (
              <div
                key={l}
                className={`rounded px-2.5 py-1.5 text-xs font-medium ${i === 0 ? "bg-brand-50 text-brand-800" : "text-ink-500"}`}
              >
                {l}
              </div>
            ))}
          </div>

          <div className="space-y-4 bg-ivory-50 p-4 text-left sm:p-5">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                ["Quality", "84"],
                ["Complexity", "76"],
                ["Open issues", "67"],
                ["Security", "91"],
              ].map(([k, v]) => (
                <div key={k} className="rounded-lg border border-line bg-white p-3">
                  <p className="text-[11px] text-ink-500">{k}</p>
                  <p className="mt-1 text-xl font-semibold tracking-tight text-ink-900">{v}</p>
                </div>
              ))}
            </div>

            <div className="rounded-lg border border-line bg-white p-3">
              <p className="text-xs font-medium text-ink-700">Code quality trend</p>
              <svg viewBox="0 0 300 120" className="mt-2 w-full" role="img" aria-label="Quality rising from 71 to 78 to 84 over three analyses">
                {[40, 70, 100].map((g) => (
                  <line key={g} x1="0" x2="300" y1={g} y2={g} stroke="#E1E9E3" strokeWidth="1" />
                ))}
                <polyline points={line} fill="none" stroke="#0F5A3F" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
                {POINTS.map((p) => (
                  <g key={p.x}>
                    <circle cx={p.x} cy={y(p.score)} r="4.5" fill="#fff" stroke="#0F5A3F" strokeWidth="2" />
                    <text x={p.x} y={y(p.score) - 10} textAnchor="middle" fontSize="10" fill="#444C47">
                      {p.score}
                    </text>
                  </g>
                ))}
              </svg>
            </div>

            <div className="overflow-x-auto rounded-lg border border-line bg-white">
              <table className="w-full min-w-[420px] text-left text-xs">
                <thead className="border-b border-line text-ink-500">
                  <tr>
                    <th className="px-3 py-2 font-medium">Repository</th>
                    <th className="px-3 py-2 font-medium">Quality</th>
                    <th className="px-3 py-2 font-medium">Issues</th>
                    <th className="px-3 py-2 font-medium">Top severity</th>
                  </tr>
                </thead>
                <tbody>
                  {ROWS.map((r) => (
                    <tr key={r.repo} className="border-b border-line last:border-0">
                      <td className="px-3 py-2 font-mono text-ink-700">{r.repo}</td>
                      <td className="px-3 py-2 text-ink-900">{r.q}</td>
                      <td className="px-3 py-2 text-ink-900">{r.issues}</td>
                      <td className="px-3 py-2">
                        <span className={`rounded px-1.5 py-0.5 font-medium ${r.sev}`}>{r.label}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <figcaption className="mt-3 text-center text-xs text-ink-400">
        Illustrative preview. Your dashboard shows your own analyses.
      </figcaption>
    </figure>
  );
}
