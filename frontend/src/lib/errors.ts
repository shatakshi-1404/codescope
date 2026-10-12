import { ApiError } from "./api";

const clean = (message: string) => message.replace(/^Value error, /, "");

export function messageOf(err: unknown): string {
  if (err instanceof ApiError) {
    // Validation errors: show the first concrete field message.
    if (err.code === "validation_error" && err.details.length > 0) {
      return clean(err.details[0].message);
    }
    return err.message;
  }
  return "Something went wrong. Please try again.";
}

/** Maps backend validation details to { fieldName: message }. */
export function fieldErrorsOf(err: unknown): Record<string, string> {
  if (!(err instanceof ApiError)) return {};
  const out: Record<string, string> = {};
  for (const d of err.details) {
    if (d.field && !out[d.field]) out[d.field] = clean(d.message);
  }
  return out;
}
