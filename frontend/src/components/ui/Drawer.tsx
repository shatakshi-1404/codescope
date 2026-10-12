import { X } from "lucide-react";
import { useRef, type ReactNode } from "react";

import { useDialogBehavior } from "../../lib/useDialogBehavior";

export function Drawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);
  useDialogBehavior(open, ref, onClose);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-ink-900/30" aria-hidden="true" onMouseDown={onClose} />
      <aside
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="absolute inset-y-0 right-0 flex w-full max-w-lg flex-col border-l border-line bg-white shadow-pop"
      >
        <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h2 className="text-sm font-semibold text-ink-900">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close panel"
            className="grid h-8 w-8 place-items-center rounded-md text-ink-500 hover:bg-sage-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">{children}</div>
      </aside>
    </div>
  );
}
