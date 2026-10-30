import { ApiError } from "./api";

const DETAIL_STATUSES = new Set([400, 409, 413, 422]);

function detailText(detail: unknown): string | null {
  if (typeof detail === "string") {
    return detail || null;
  }
  if (Array.isArray(detail)) {
    return detail.length > 0 ? detailText(detail[0]) : null;
  }
  if (detail && typeof detail === "object") {
    const { msg, message } = detail as { msg?: unknown; message?: unknown };
    if (typeof msg === "string" && msg) {
      return msg;
    }
    if (typeof message === "string" && message) {
      return message;
    }
  }
  return null;
}

export function documentErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    if (DETAIL_STATUSES.has(error.status)) {
      return detailText(error.detail) ?? fallback;
    }
    if (error.status === 403) {
      return "Solo quien subió el documento o un administrador puede editarlo.";
    }
  }
  return fallback;
}
