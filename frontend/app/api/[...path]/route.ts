// Server-side proxy to the FastAPI backend. Runs on the server only, so the backend
// URL is never exposed to the browser and no secrets are shipped to the client.
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = (process.env.REPORADAR_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const MAX_BODY_BYTES = 4096;
const ALLOWED_SEGMENT = /^[A-Za-z0-9._~%+-]+$/;

async function proxy(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (path.some((segment) => !ALLOWED_SEGMENT.test(segment))) {
    return NextResponse.json({ error: "Not found." }, { status: 404 });
  }

  const target = new URL(`${BACKEND_URL}/api/${path.join("/")}`);
  target.search = req.nextUrl.search;

  const headers: Record<string, string> = { Accept: "application/json" };
  const forwardedFor = req.headers.get("x-forwarded-for");
  if (forwardedFor) headers["X-Forwarded-For"] = forwardedFor;

  let body: string | undefined;
  if (req.method === "POST") {
    body = await req.text();
    if (body.length > MAX_BODY_BYTES) {
      return NextResponse.json({ error: "Request body is too large." }, { status: 413 });
    }
    headers["Content-Type"] = "application/json";
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, { method: req.method, headers, body, cache: "no-store" });
  } catch {
    return NextResponse.json(
      { error: "The RepoRadar API is unreachable. Is the backend running?" },
      { status: 503 },
    );
  }

  const responseHeaders = new Headers();
  responseHeaders.set("Content-Type", upstream.headers.get("content-type") ?? "application/json");
  responseHeaders.set("Cache-Control", upstream.headers.get("cache-control") ?? "no-store");
  const retryAfter = upstream.headers.get("retry-after");
  if (retryAfter) responseHeaders.set("Retry-After", retryAfter);

  return new NextResponse(await upstream.arrayBuffer(), { status: upstream.status, headers: responseHeaders });
}

export { proxy as GET, proxy as POST };
