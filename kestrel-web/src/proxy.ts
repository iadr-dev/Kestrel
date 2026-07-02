import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Protect dashboard routes — redirect to login if no token cookie
  if (pathname.startsWith("/dashboard")) {
    // Note: Token is in localStorage (client-side), not cookies.
    // Full server-side auth check would require cookie-based sessions.
    // For now, let all requests through — client-side auth guard handles the rest.
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Match all paths except static files and API routes
    "/((?!api|_next/static|_next/image|favicon.ico|icon.png|logo.png|landing).*)",
  ],
};
