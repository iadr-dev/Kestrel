import type { NextRequest } from "next/server";

// Streaming passthrough for the server push bus (SSE).
//
// The global Next.js rewrite (/api/:path* → backend) BUFFERS the whole response
// body, which kills SSE. A Route Handler takes precedence over the rewrite, so this
// streams the upstream ReadableStream straight through — same approach as the agent
// chat proxy. Only this one path is handled here; everything else falls through to
// the rewrite untouched.

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";

export async function GET(request: NextRequest): Promise<Response> {
  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  headers.set("accept", "text/event-stream");

  const upstream = await fetch(`${BACKEND}/api/v1/events/stream`, {
    method: "GET",
    headers,
    cache: "no-store",
  });

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
