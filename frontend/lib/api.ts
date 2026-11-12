// Client-side API helpers. Every request goes through the Next.js proxy at /api,
// so the backend URL and all secrets stay on the server.
import type { MethodologyData } from "@/components/MethodologyData";
import type { ContributionsResponse, Generated, Report, Validation } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly retryAfter?: number;

  constructor(message: string, status: number, retryAfter?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api/${path}`, {
      ...init,
      cache: "no-store",
      headers: { Accept: "application/json", ...(init.headers ?? {}) },
    });
  } catch {
    throw new ApiError(
      "Can't reach the RepoRadar web server. Make sure it is running (npm run dev or npm start) and try again.",
      0,
    );
  }

  if (!res.ok) {
    let message = `Request failed with status ${res.status}.`;
    try {
      const body = (await res.json()) as { error?: string; detail?: string };
      message = body.error ?? body.detail ?? message;
    } catch {
      // Non-JSON error body: keep the generic message.
    }
    const retry = Number(res.headers.get("Retry-After"));
    throw new ApiError(message, res.status, Number.isFinite(retry) && retry > 0 ? retry : undefined);
  }
  return (await res.json()) as T;
}

const enc = encodeURIComponent;

export const api = {
  validate: (repo: string, signal?: AbortSignal) =>
    request<Validation>(`validate?repo=${enc(repo)}`, { signal }),

  report: (owner: string, repo: string) => request<Report>(`repos/${enc(owner)}/${enc(repo)}/report`),

  generate: (owner: string, repo: string, kind: string) =>
    request<Generated>(`repos/${enc(owner)}/${enc(repo)}/generate/${enc(kind)}`),

  createShare: (repo: string) =>
    request<{ id: string; path: string }>("reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo }),
    }),

  sharedReport: (id: string) => request<Report>(`reports/${enc(id)}`),

  methodology: () => request<MethodologyData>("methodology"),

  contributions: (label: string, q: string, page: number) => {
    const params = new URLSearchParams({ label, page: String(page) });
    if (q.trim()) params.set("q", q.trim());
    return request<ContributionsResponse>(`contributions?${params.toString()}`);
  },
};
