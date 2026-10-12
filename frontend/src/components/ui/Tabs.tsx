import type { KeyboardEvent } from "react";

export interface TabDef<T extends string> {
  id: T;
  label: string;
}

export const tabDomId = (prefix: string, id: string) => `${prefix}-tab-${id}`;
export const panelDomId = (prefix: string, id: string) => `${prefix}-panel-${id}`;

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  label,
  prefix,
}: {
  tabs: readonly TabDef<T>[];
  value: T;
  onChange: (id: T) => void;
  label: string;
  prefix: string;
}) {
  function onKey(e: KeyboardEvent<HTMLDivElement>) {
    const index = tabs.findIndex((t) => t.id === value);
    let next = -1;
    if (e.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    if (next === -1) return;
    e.preventDefault();
    onChange(tabs[next].id);
    document.getElementById(tabDomId(prefix, tabs[next].id))?.focus();
  }

  return (
    <div className="overflow-x-auto border-b border-line">
      <div role="tablist" aria-label={label} onKeyDown={onKey} className="flex min-w-max gap-1">
        {tabs.map((t) => {
          const selected = t.id === value;
          return (
            <button
              key={t.id}
              id={tabDomId(prefix, t.id)}
              role="tab"
              aria-selected={selected}
              aria-controls={panelDomId(prefix, t.id)}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(t.id)}
              className={
                "-mb-px border-b-2 px-3.5 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500 " +
                (selected ? "border-brand-700 text-brand-800" : "border-transparent text-ink-500 hover:text-ink-900")
              }
            >
              {t.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
