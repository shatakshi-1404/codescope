import type { AnalysisStatus } from "./types";

const dateFmt = new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat(undefined, {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export const formatDate = (iso: string) => dateFmt.format(new Date(iso));
export const formatDateTime = (iso: string) => dateTimeFmt.format(new Date(iso));
export const formatNumber = (n: number) => n.toLocaleString();

export function timeAgo(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} d ago`;
  return formatDate(iso);
}

/** Text colour for a 0-100 score. Always shown next to the number, never as the only signal. */
export function scoreTone(score: number): string {
  if (score >= 80) return "text-brand-700";
  if (score >= 65) return "text-amber-700";
  return "text-red-700";
}

export const isActive = (status?: AnalysisStatus | null): boolean =>
  status === "PENDING" || status === "RUNNING";

export function scoreLabel(score: number): string {
  if (score >= 90) return "Excellent";
  if (score >= 80) return "Good";
  if (score >= 65) return "Fair";
  if (score >= 50) return "Needs attention";
  return "Poor";
}

export const shortSha = (sha?: string | null): string => (sha ? sha.slice(0, 7) : "—");
