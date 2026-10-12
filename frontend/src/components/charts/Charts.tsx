import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ReactNode } from "react";

import type { Severity } from "../../lib/types";

const AXIS = { fontSize: 11, fill: "#7C857F" };
const GRID = "#E1E9E3";
const TOOLTIP_STYLE = {
  border: "1px solid #CBD8CF",
  borderRadius: 8,
  fontSize: 12,
  boxShadow: "0 8px 24px rgba(15,60,40,0.10)",
};

export const SEVERITY_ORDER: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
export const SEVERITY_COLORS: Record<Severity, string> = {
  CRITICAL: "#B91C1C",
  HIGH: "#EA580C",
  MEDIUM: "#D97706",
  LOW: "#7F9C88",
};
const label = (s: string) => s.charAt(0) + s.slice(1).toLowerCase();

function shortDate(d: string): string {
  const date = new Date(`${d}T00:00:00`);
  return Number.isNaN(date.getTime()) ? d : date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="card p-5">
      <h3 className="text-sm font-semibold text-ink-900">{title}</h3>
      {subtitle && <p className="mt-0.5 text-xs text-ink-500">{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function TrendLine({
  data,
  dataKey,
  name,
  color = "#0F5A3F",
  domain,
  height = 220,
  xKey = "date",
}: {
  data: object[];
  dataKey: string;
  name: string;
  color?: string;
  domain?: [number, number];
  height?: number;
  xKey?: string;
}) {
  return (
    <div style={{ height }} role="img" aria-label={`${name} over time`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis
            dataKey={xKey}
            tickFormatter={xKey === "date" ? shortDate : undefined}
            tick={AXIS}
            tickLine={false}
            axisLine={{ stroke: GRID }}
            minTickGap={24}
          />
          <YAxis domain={domain} tick={AXIS} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [String(v), name] as [string, string]} />
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2.5}
            dot={{ r: 3, fill: "#fff", stroke: color, strokeWidth: 2 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SeverityBars({ counts, height = 220 }: { counts: Record<string, number>; height?: number }) {
  const data = SEVERITY_ORDER.map((s) => ({ name: label(s), key: s, count: counts[s] ?? 0 }));
  return (
    <div style={{ height }} role="img" aria-label={`Findings by severity: ${data.map((d) => `${d.name} ${d.count}`).join(", ")}`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="name" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} />
          <YAxis allowDecimals={false} tick={AXIS} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "#EEF6F1" }} formatter={(v) => [String(v), "Findings"] as [string, string]} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
            {data.map((d) => (
              <Cell key={d.key} fill={SEVERITY_COLORS[d.key]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SeverityDonut({ counts, centerLabel }: { counts: Record<string, number>; centerLabel: string }) {
  const rows = SEVERITY_ORDER.map((s) => ({ name: label(s), key: s, value: counts[s] ?? 0 }));
  const total = rows.reduce((sum, r) => sum + r.value, 0);
  const data = rows.filter((r) => r.value > 0);

  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row">
      <div className="relative h-[170px] w-[170px] shrink-0" role="img" aria-label={`${total} ${centerLabel}`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={54} outerRadius={80} paddingAngle={2} stroke="none">
              {data.map((d) => (
                <Cell key={d.key} fill={SEVERITY_COLORS[d.key]} />
              ))}
            </Pie>
            <Tooltip contentStyle={TOOLTIP_STYLE} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
          <div>
            <p className="text-2xl font-semibold tracking-tight text-ink-900">{total}</p>
            <p className="text-[11px] text-ink-500">{centerLabel}</p>
          </div>
        </div>
      </div>
      <ul className="w-full space-y-2 text-sm">
        {rows.map((r) => (
          <li key={r.key} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-ink-600">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: SEVERITY_COLORS[r.key] }} aria-hidden="true" />
              {r.name}
            </span>
            <span className="font-medium tabular-nums text-ink-900">{r.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
