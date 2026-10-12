export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" className="shrink-0">
      <rect width="32" height="32" rx="8" fill="#0F5A3F" />
      <circle cx="15" cy="15" r="7" fill="none" stroke="#fff" strokeWidth="2.5" />
      <path d="M20.5 20.5 26 26" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <Logo />
      <span className="text-[17px] font-semibold tracking-tight text-ink-900">CodeScope</span>
    </span>
  );
}
