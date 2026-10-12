import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, CircleAlert, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { BarList } from "../charts/BarList";
import { ChartCard, SeverityBars, TrendLine } from "../charts/Charts";
import { SeverityBadge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Skeleton } from "../ui/Skeleton";
import { EmptyState, ErrorState } from "../ui/States";
import { api, type FileSort } from "../../lib/endpoints";
import { messageOf } from "../../lib/errors";
import { formatDate, formatNumber, scoreTone, shortSha } from "../../lib/format";
import type { Cluster, ReportData } from "../../lib/types";

const label = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replace("-", " ");

function Stat({ title, value, hint }: { title: string; value: string; hint?: string }) {
  return (
    <div className="card p-5">
      <p className="text-sm text-ink-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums text-ink-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-500">{hint}</p>}
    </div>
  );
}

// ---------------------------------------------------------------- Quality
export function QualitySection({ report }: { report: ReportData }) {
  const q = report.quality;
  const status = q.issues_by_status;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat title="Open" value={formatNumber(status.OPEN ?? 0)} />
        <Stat title="Resolved" value={formatNumber(status.RESOLVED ?? 0)} />
        <Stat title="Ignored" value={formatNumber(status.IGNORED ?? 0)} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Issues by severity">
          <SeverityBars counts={q.issues_by_severity} />
        </ChartCard>
        <ChartCard title="Issues by category">
          <BarList rows={Object.entries(q.issues_by_category).map(([k, v]) => ({ label: label(k), value: v }))} emptyText="No issues found." />
        </ChartCard>
      </div>
      {q.top_rules.length > 0 && (
        <ChartCard title="Most frequent rules">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] text-left text-sm">
              <thead className="text-xs text-ink-500">
                <tr>
                  <th scope="col" className="pb-2 font-medium">Rule</th>
                  <th scope="col" className="pb-2 font-medium">Description</th>
                  <th scope="col" className="pb-2 text-right font-medium">Count</th>
                </tr>
              </thead>
              <tbody>
                {q.top_rules.map((r) => (
                  <tr key={r.rule_id} className="border-t border-line">
                    <td className="py-2.5 font-mono text-xs text-ink-500">{r.rule_id}</td>
                    <td className="py-2.5 text-ink-800">{r.name}</td>
                    <td className="py-2.5 text-right tabular-nums font-medium">{r.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>
      )}
    </div>
  );
}

// ------------------------------------------------------------- Complexity
export function ComplexitySection({ report }: { report: ReportData }) {
  const c = report.complexity;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Stat title="Average cyclomatic complexity" value={c.avg_cyclomatic.toFixed(2)} hint="Per function. Lower is easier to maintain." />
        <Stat title="Highest in any function" value={String(c.max_cyclomatic)} hint="Functions above 15 are flagged." />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Files by their most complex function" subtitle="Cyclomatic complexity ranges">
          <BarList rows={c.distribution.map((d) => ({ label: d.label, value: d.files, hint: d.files === 1 ? "file" : "files" }))} />
        </ChartCard>
        <ChartCard title="Most complex files">
          {c.most_complex_files.length === 0 ? (
            <p className="py-6 text-center text-sm text-ink-500">No functions found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[380px] text-left text-sm">
                <thead className="text-xs text-ink-500">
                  <tr>
                    <th scope="col" className="pb-2 font-medium">File</th>
                    <th scope="col" className="pb-2 text-right font-medium">Max</th>
                    <th scope="col" className="pb-2 text-right font-medium">Avg</th>
                  </tr>
                </thead>
                <tbody>
                  {c.most_complex_files.map((f) => (
                    <tr key={f.path} className="border-t border-line">
                      <td className="max-w-[220px] truncate py-2.5 font-mono text-[13px] text-ink-800" title={f.path}>{f.path}</td>
                      <td className="py-2.5 text-right tabular-nums font-medium">{f.max_complexity}</td>
                      <td className="py-2.5 text-right tabular-nums text-ink-600">{f.avg_complexity.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ChartCard>
      </div>
    </div>
  );
}

// --------------------------------------------------------------- Security
function SecurityFindings({ analysisId, ruleNames }: { analysisId: number; ruleNames: Record<string, string> }) {
  const [limit, setLimit] = useState(20);
  const q = useQuery({
    queryKey: ["security", analysisId, limit],
    queryFn: () => api.analysisSecurity(analysisId, limit),
    placeholderData: (prev) => prev,
  });

  if (q.isPending) return <Skeleton className="h-40" />;
  if (q.isError) return <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />;

  return (
    <div className="space-y-3">
      <ul className="space-y-3">
        {q.data.items.map((f) => (
          <li key={f.id} className="card p-4">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={f.severity} />
              <span className="text-sm font-medium text-ink-900">{ruleNames[f.rule_id] ?? f.rule_id}</span>
              <span className="font-mono text-xs text-ink-400">{f.rule_id}</span>
            </div>
            <p className="mt-2 break-all font-mono text-[13px] text-ink-600">{f.file}:{f.line}</p>
            <p className="mt-2 text-sm leading-relaxed text-ink-700">{f.description}</p>
            <p className="mt-2 text-sm leading-relaxed text-brand-800"><span className="font-medium">Recommendation:</span> {f.recommendation}</p>
          </li>
        ))}
      </ul>
      {q.data.total > q.data.items.length && (
        <div className="text-center">
          <Button variant="secondary" onClick={() => setLimit((l) => l + 20)} loading={q.isFetching}>
            Show more ({q.data.total - q.data.items.length} remaining)
          </Button>
        </div>
      )}
    </div>
  );
}

export function SecuritySection({ report }: { report: ReportData }) {
  const s = report.security;
  const ruleNames = Object.fromEntries(s.by_rule.map((r) => [r.rule_id, r.name]));
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <p><strong className="font-semibold">{s.label}.</strong> {s.disclaimer}</p>
      </div>

      {s.total === 0 ? (
        <EmptyState icon={ShieldCheck} title="No findings from the static checks" text="That does not prove the code is secure. These checks cover a limited set of patterns." />
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Findings by severity"><SeverityBars counts={s.by_severity} /></ChartCard>
            <ChartCard title="Findings by check">
              <BarList rows={s.by_rule.map((r) => ({ label: r.name, value: r.count }))} />
            </ChartCard>
          </div>
          <SecurityFindings analysisId={report.analysis.id} ruleNames={ruleNames} />
        </>
      )}
    </div>
  );
}

// ----------------------------------------------------------- Architecture
export function ArchitectureSection({ report }: { report: ReportData }) {
  const a = report.architecture;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Languages" subtitle="Lines of code">
          <BarList rows={a.languages.map((l) => ({ label: label(l.language), value: l.lines, hint: `${l.files} files` }))} />
        </ChartCard>
        <ChartCard title="Top-level directories" subtitle="Lines of code">
          <BarList rows={a.directories.map((d) => ({ label: d.name, value: d.lines, hint: `${d.files} files`, mono: true }))} />
        </ChartCard>
      </div>
      <ChartCard title="Largest files">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] text-left text-sm">
            <thead className="text-xs text-ink-500">
              <tr>
                <th scope="col" className="pb-2 font-medium">File</th>
                <th scope="col" className="pb-2 text-right font-medium">Lines</th>
                <th scope="col" className="pb-2 text-right font-medium">Functions</th>
              </tr>
            </thead>
            <tbody>
              {a.largest_files.map((f) => (
                <tr key={f.path} className="border-t border-line">
                  <td className="max-w-[360px] truncate py-2.5 font-mono text-[13px] text-ink-800" title={f.path}>{f.path}</td>
                  <td className="py-2.5 text-right tabular-nums">{formatNumber(f.lines_of_code)}</td>
                  <td className="py-2.5 text-right tabular-nums text-ink-600">{f.functions}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>
    </div>
  );
}

// ------------------------------------------------------------------ Files
const FILE_LIMIT = 25;

export function FilesSection({ analysisId }: { analysisId: number }) {
  const [sort, setSort] = useState<FileSort>("complexity");
  const [descending, setDescending] = useState(true);
  const [offset, setOffset] = useState(0);

  const q = useQuery({
    queryKey: ["files", analysisId, sort, descending, offset],
    queryFn: () => api.files(analysisId, { sort, descending, limit: FILE_LIMIT, offset }),
    placeholderData: (prev) => prev,
  });

  function toggle(col: FileSort) {
    if (col === sort) setDescending((d) => !d);
    else {
      setSort(col);
      setDescending(col !== "path");
    }
    setOffset(0);
  }

  function SortTh({ col, children, right }: { col: FileSort; children: string; right?: boolean }) {
    const active = sort === col;
    return (
      <th scope="col" aria-sort={active ? (descending ? "descending" : "ascending") : "none"} className={`px-4 py-2.5 font-medium ${right ? "text-right" : ""}`}>
        <button
          onClick={() => toggle(col)}
          className={`inline-flex items-center gap-1 rounded hover:text-ink-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${active ? "text-ink-900" : ""}`}
        >
          {children}
          {active && (descending ? <ArrowDown className="h-3 w-3" aria-hidden="true" /> : <ArrowUp className="h-3 w-3" aria-hidden="true" />)}
        </button>
      </th>
    );
  }

  if (q.isPending) return <Skeleton className="h-64" />;
  if (q.isError) return <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />;
  const { items, total } = q.data;

  return (
    <div className="space-y-4">
      <div className={`card overflow-x-auto transition-opacity ${q.isFetching ? "opacity-70" : ""}`}>
        <table className="w-full min-w-[760px] text-left text-sm">
          <caption className="sr-only">Analyzed files</caption>
          <thead className="border-b border-line bg-ivory-50 text-xs text-ink-500">
            <tr>
              <SortTh col="path">File</SortTh>
              <th scope="col" className="px-4 py-2.5 font-medium">Language</th>
              <SortTh col="lines" right>Lines</SortTh>
              <SortTh col="functions" right>Functions</SortTh>
              <SortTh col="complexity" right>Max complexity</SortTh>
              <th scope="col" className="px-4 py-2.5 text-right font-medium">Issues</th>
            </tr>
          </thead>
          <tbody>
            {items.map((f) => (
              <tr key={f.path} className="border-b border-line last:border-0 hover:bg-ivory-50">
                <td className="max-w-[320px] truncate px-4 py-3 font-mono text-[13px] text-ink-800" title={f.path}>{f.path}</td>
                <td className="px-4 py-3 capitalize text-ink-600">{f.language}</td>
                <td className="px-4 py-3 text-right tabular-nums">{formatNumber(f.lines_of_code)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{f.function_count}</td>
                <td className="px-4 py-3 text-right tabular-nums">{f.max_complexity}</td>
                <td className="px-4 py-3 text-right tabular-nums">{f.issue_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total > FILE_LIMIT && (
        <div className="flex items-center justify-between text-sm text-ink-500">
          <span>{offset + 1}–{Math.min(offset + FILE_LIMIT, total)} of {formatNumber(total)}</span>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => setOffset((o) => Math.max(0, o - FILE_LIMIT))} disabled={offset === 0}>Previous</Button>
            <Button variant="secondary" size="sm" onClick={() => setOffset((o) => o + FILE_LIMIT)} disabled={offset + FILE_LIMIT >= total}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}

// --------------------------------------------------------------- Insights
function ClusterCard({ c }: { c: Cluster }) {
  return (
    <li className="card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={c.highest_severity} />
        <span className="text-sm font-medium text-ink-900">{c.label}</span>
        <span className="ml-auto text-sm tabular-nums text-ink-500">{c.size} {c.size === 1 ? "finding" : "findings"}</span>
      </div>
      {c.top_files.length > 0 && (
        <p className="mt-2 truncate font-mono text-xs text-ink-500" title={c.top_files.join(", ")}>
          Mostly in {c.top_files.join(", ")}
        </p>
      )}
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {c.top_terms.map((t) => <span key={t} className="rounded bg-sage-100 px-1.5 py-0.5 text-xs text-ink-600">{t}</span>)}
        {c.rule_ids.map((r) => <span key={r} className="rounded border border-line px-1.5 py-0.5 font-mono text-xs text-ink-400">{r}</span>)}
      </div>
    </li>
  );
}

export function InsightsSection({ analysisId }: { analysisId: number }) {
  const q = useQuery({ queryKey: ["insights", analysisId], queryFn: () => api.insights(analysisId) });
  if (q.isPending) return <Skeleton className="h-64" />;
  if (q.isError) return <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />;
  const d = q.data;

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3 rounded-lg border border-brand-200 bg-brand-50 p-4 text-sm text-brand-900">
        <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
        <p><strong className="font-semibold">{d.label}.</strong> {d.method} Findings from the deterministic analyzer are the source of truth.</p>
      </div>

      <section className="card p-5">
        <h3 className="text-sm font-semibold text-ink-900">Suggested next steps</h3>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-ink-700">
          {d.recommendations.map((r) => <li key={r}>{r}</li>)}
        </ol>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-ink-900">Grouped issues</h3>
        {d.issue_clusters.length === 0 ? <p className="text-sm text-ink-500">No issues to group.</p> : (
          <ul className="grid gap-3 lg:grid-cols-2">{d.issue_clusters.map((c, i) => <ClusterCard key={`${c.label}-${i}`} c={c} />)}</ul>
        )}
        {d.truncated && <p className="text-xs text-ink-400">Grouping covers the {d.clustered_issue_count.toLocaleString()} most severe issues.</p>}
      </section>

      {d.security_clusters.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-ink-900">Grouped security findings</h3>
          <ul className="grid gap-3 lg:grid-cols-2">{d.security_clusters.map((c, i) => <ClusterCard key={`${c.label}-${i}`} c={c} />)}</ul>
        </section>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- History
export function HistorySection({ repositoryId, currentId }: { repositoryId: number; currentId: number }) {
  const q = useQuery({ queryKey: ["history", repositoryId], queryFn: () => api.history(repositoryId) });
  if (q.isPending) return <Skeleton className="h-72" />;
  if (q.isError) return <ErrorState message={messageOf(q.error)} onRetry={() => q.refetch()} />;

  const points = q.data;
  if (points.length === 0) return <EmptyState icon={CircleAlert} title="No completed analyses yet" />;
  const data = points.map((p) => ({ ...p, label: `#${p.number}` }));

  return (
    <div className="space-y-4">
      {points.length < 2 && (
        <p className="rounded-lg border border-line bg-white p-4 text-sm text-ink-600">
          This is the only completed analysis so far. Run it again after making changes to see how your scores move.
        </p>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Quality over time" subtitle="Overall score per analysis">
          <TrendLine data={data} xKey="label" dataKey="overall" name="Quality" domain={[0, 100]} />
        </ChartCard>
        <ChartCard title="Issue count over time">
          <TrendLine data={data} xKey="label" dataKey="issue_count" name="Issues" color="#D97706" />
        </ChartCard>
        <ChartCard title="Complexity over time" subtitle="Average cyclomatic complexity (lower is better)">
          <TrendLine data={data} xKey="label" dataKey="avg_complexity" name="Avg. complexity" color="#667F6F" />
        </ChartCard>
        <ChartCard title="Security findings over time" subtitle="Static checks only">
          <TrendLine data={data} xKey="label" dataKey="security_finding_count" name="Findings" color="#B91C1C" />
        </ChartCard>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[620px] text-left text-sm">
          <caption className="sr-only">Analysis history</caption>
          <thead className="border-b border-line bg-ivory-50 text-xs text-ink-500">
            <tr>
              <th scope="col" className="px-4 py-2.5 font-medium">Analysis</th>
              <th scope="col" className="px-4 py-2.5 font-medium">Date</th>
              <th scope="col" className="px-4 py-2.5 font-medium">Commit</th>
              <th scope="col" className="px-4 py-2.5 text-right font-medium">Quality</th>
              <th scope="col" className="px-4 py-2.5 text-right font-medium">Issues</th>
              <th scope="col" className="px-4 py-2.5 text-right font-medium">Security</th>
            </tr>
          </thead>
          <tbody>
            {[...points].reverse().map((p) => (
              <tr key={p.analysis_id} className={`border-b border-line last:border-0 ${p.analysis_id === currentId ? "bg-brand-50/60" : ""}`}>
                <td className="px-4 py-3">
                  {p.analysis_id === currentId ? (
                    <span className="font-medium text-ink-900">#{p.number} <span className="text-xs font-normal text-brand-700">(this report)</span></span>
                  ) : (
                    <Link to={`/analyses/${p.analysis_id}`} className="font-medium text-brand-700 hover:underline">#{p.number}</Link>
                  )}
                </td>
                <td className="px-4 py-3 text-ink-600">{formatDate(p.date)}</td>
                <td className="px-4 py-3 font-mono text-[13px] text-ink-600">{shortSha(p.commit_sha)}</td>
                <td className={`px-4 py-3 text-right font-semibold tabular-nums ${scoreTone(p.overall)}`}>{Math.round(p.overall)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{p.issue_count}</td>
                <td className="px-4 py-3 text-right tabular-nums">{p.security_finding_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
