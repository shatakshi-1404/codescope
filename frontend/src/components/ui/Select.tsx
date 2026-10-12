import type { SelectHTMLAttributes } from "react";

export function Select({ className = "", ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={
        "h-9 rounded-md border border-line-strong bg-white px-2.5 text-sm text-ink-900 " +
        "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:opacity-60 " +
        className
      }
      {...rest}
    />
  );
}
