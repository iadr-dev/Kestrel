import type { NextRequest } from "next/server";

// Streaming passthrough proxy — ONLY for the SSE chat endpoints.
//
// The global Next.js rewrite (next.config.ts: /api/:path* → backend) BUFFERS the
// whole response body before releasing it, which kills SSE. Route Handlers take
// precedence over rewrites, so this handler streams the upstream ReadableStream
// straight through chunk-by-chunk (the claude.ai approach: nothing buffers).
//
// CRITICAL: only the streaming paths are proxied here. Plain-JSON agent endpoints
// (sessions list, session restore, skills, cost, …) MUST fall through to the rewrite
// untouched — proxying them through this stream-shaped handler corrupted their JSON
// (it forced text/event-stream), breaking session restore + recents on page refresh.

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

// Sub-paths under /api/v1/agent/ that return SSE and must stream unbuffered.
const STREAMING_PATHS = new Set([
  "chat/stream",
  "chat/retry",
  "chat/edit",
  "chat/clarify",
]);

function isStreaming(path: string[]): boolean {
  return STREAMING_PATHS.has(path.join("/"));
}

async function proxyStream(request: NextRequest, path: string[]): Promise<Response> {
  const search = request.nextUrl.search;
  const target = `${BACKEND}/api/v1/agent/${path.join("/")}${search}`;

  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  const ct = request.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  headers.set("accept", "text/event-stream");

  const method = request.method;
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();

  const upstream = await fetch(target, { method, headers, body, cache: "no-store" });

  // Returning the upstream ReadableStream directly (not awaiting .text()/.json())
  // is what keeps it streaming chunk-by-chunk.
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") || "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}

// Forward non-streaming requests to the backend with the body/headers intact and
// the response (JSON) returned as-is. Used for GET sessions/skills/etc. so they
// don't get stream-mangled (and so they still work even though this route handler
// shadows the rewrite for the whole /agent/* subtree).
async function proxyJson(request: NextRequest, path: string[]): Promise<Response> {
  const search = request.nextUrl.search;
  const target = `${BACKEND}/api/v1/agent/${path.join("/")}${search}`;

  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  const ct = request.headers.get("content-type");
  if (ct) headers.set("content-type", ct);

  const method = request.method;
  const body = method === "GET" || method === "HEAD" ? undefined : await request.text();

  const upstream = await fetch(target, { method, headers, body, cache: "no-store" });
  const respBody = await upstream.text();
  return new Response(respBody, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("content-type") || "application/json" },
  });
}

export async function POST(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return isStreaming(path) ? proxyStream(request, path) : proxyJson(request, path);
}

export async function GET(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return isStreaming(path) ? proxyStream(request, path) : proxyJson(request, path);
}

export async function DELETE(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxyJson(request, path);
}
