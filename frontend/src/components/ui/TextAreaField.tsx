import { useId, type TextareaHTMLAttributes } from "react";

interface Props extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  hint?: string;
}

export function TextAreaField({ label, error, hint, id, className = "", ...rest }: Props) {
  const autoId = useId();
  const textId = id ?? autoId;
  return (
    <div className="space-y-1.5">
      <label htmlFor={textId} className="block text-sm font-medium text-ink-700">
        {label}
      </label>
      <textarea
        id={textId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${textId}-error` : hint ? `${textId}-hint` : undefined}
        className={
          "min-h-[88px] w-full rounded-md border bg-white px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-2 " +
          (error ? "border-red-400 focus:ring-red-200 " : "border-line-strong focus:border-brand-500 focus:ring-brand-200 ") +
          className
        }
        {...rest}
      />
      {error ? (
        <p id={`${textId}-error`} role="alert" className="text-xs text-red-700">
          {error}
        </p>
      ) : hint ? (
        <p id={`${textId}-hint`} className="text-xs text-ink-500">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
